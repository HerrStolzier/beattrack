#!/usr/bin/env node

import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(scriptDir, "..");

function stripQuotes(value) {
  if (
    (value.startsWith('"') && value.endsWith('"')) ||
    (value.startsWith("'") && value.endsWith("'"))
  ) {
    return value.slice(1, -1);
  }
  return value;
}

function loadEnvFile(relativePath) {
  const filePath = resolve(repoRoot, relativePath);
  if (!existsSync(filePath)) return;

  for (const rawLine of readFileSync(filePath, "utf8").split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;

    const eqIndex = line.indexOf("=");
    if (eqIndex === -1) continue;

    const key = line.slice(0, eqIndex).trim();
    const value = stripQuotes(line.slice(eqIndex + 1).trim());
    if (key && process.env[key] === undefined) {
      process.env[key] = value;
    }
  }
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    signal: AbortSignal.timeout(10_000),
  });

  const text = await response.text();
  let body = text;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }

  return {
    ok: response.ok,
    status: response.status,
    body,
  };
}

loadEnvFile("apps/api/.env");
loadEnvFile("apps/web/.env.local");

const apiBaseUrl =
  process.env.BEATTRACK_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "https://beattrack-production.up.railway.app";

const supabaseUrl =
  process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey =
  process.env.SUPABASE_SERVICE_ROLE_KEY ||
  process.env.SUPABASE_ANON_KEY ||
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

const summary = {
  checkedAt: new Date().toISOString(),
  api: { url: `${apiBaseUrl}/health` },
  apiSongCount: { url: `${apiBaseUrl}/songs/count/total` },
  apiSongSearch: { url: `${apiBaseUrl}/songs?q=daft&limit=1` },
  supabase: { url: supabaseUrl ? `${supabaseUrl}/rest/v1/` : null },
  analysisJobs: { url: supabaseUrl ? `${supabaseUrl}/rest/v1/analysis_jobs` : null },
};

let failed = false;

try {
  const apiResult = await fetchJson(`${apiBaseUrl}/health`);
  summary.api = {
    ...summary.api,
    status: apiResult.status,
    ok: apiResult.ok,
    body: apiResult.body,
  };
  if (!apiResult.ok) failed = true;
} catch (error) {
  summary.api = {
    ...summary.api,
    ok: false,
    error: error instanceof Error ? error.message : String(error),
  };
  failed = true;
}

for (const [key, url] of [
  ["apiSongCount", `${apiBaseUrl}/songs/count/total`],
  ["apiSongSearch", `${apiBaseUrl}/songs?q=daft&limit=1`],
]) {
  try {
    const result = await fetchJson(url);
    summary[key] = {
      ...summary[key],
      status: result.status,
      ok: result.ok,
      body: result.body,
    };
    if (!result.ok) failed = true;
  } catch (error) {
    summary[key] = {
      ...summary[key],
      ok: false,
      error: error instanceof Error ? error.message : String(error),
    };
    failed = true;
  }
}

if (!supabaseUrl || !supabaseKey) {
  summary.supabase = {
    ...summary.supabase,
    ok: false,
    error: "Missing SUPABASE_URL/NEXT_PUBLIC_SUPABASE_URL or a Supabase key",
  };
  failed = true;
} else {
  const supabaseChecks = [
    {
      key: "supabase",
      url: new URL("/rest/v1/config", supabaseUrl),
      params: {
        select: "key",
        key: "eq.normalization_stats",
        limit: "1",
      },
    },
    {
      key: "analysisJobs",
      url: new URL("/rest/v1/analysis_jobs", supabaseUrl),
      params: {
        select: "id,status,created_at",
        order: "created_at.desc",
        limit: "1",
      },
    },
  ];

  for (const check of supabaseChecks) {
    for (const [name, value] of Object.entries(check.params)) {
      check.url.searchParams.set(name, value);
    }

    try {
      const supabaseResult = await fetchJson(check.url.toString(), {
        headers: {
          apikey: supabaseKey,
          Authorization: `Bearer ${supabaseKey}`,
        },
      });
      summary[check.key] = {
        ...summary[check.key],
        status: supabaseResult.status,
        ok: supabaseResult.ok,
        body: supabaseResult.body,
      };
      if (!supabaseResult.ok) failed = true;
    } catch (error) {
      summary[check.key] = {
        ...summary[check.key],
        ok: false,
        error: error instanceof Error ? error.message : String(error),
      };
      failed = true;
    }
  }
}

console.log(JSON.stringify(summary, null, 2));
process.exitCode = failed ? 1 : 0;
