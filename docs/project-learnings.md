# Project Learnings

## Overview

Durable learnings from recent `beattrack` work. This file holds practical implementation caveats that are too detailed for `AGENTS.md` but still worth keeping.

## Stable Learnings

- Paginated song and similarity queries need deterministic `ORDER BY` clauses before slicing or pagination logic. Without that, results can look flaky even when the data is correct.
- Avoid blanket layout rules like `body > * { position: relative; }`. They can silently break `position: fixed` overlays, gradients, and effect layers.
- Analysis job state must live in Postgres, not process memory. Railway restarts and multiple instances can otherwise make clients see "Job not found" for valid uploads.
- Keep route modules focused on HTTP behavior. Worker and script logic should prefer import-safe service modules so tests and batch scripts do not accidentally initialize Procrastinate.

## Workflow Gotchas

- Guard browser-only APIs such as `matchMedia` in tests and non-browser environments.
- Visual overlay work needs both desktop and mobile checks. Effects that look subtle on desktop can block content or overwhelm small screens.
- Before large work, sort `git status --short` into intentional product changes, docs, runtime artifacts, generated data, and unrelated user changes.
- Long-running data scripts should write checkpoints and logs outside the committed source tree unless a file is intentionally used as a fixture or seed list.

## Infra / Deploy Notes

- Keep local pre-commit checks lightweight and let CI carry heavier validation when workspace-level tooling or hoisting makes local frontend linting brittle.
- Supabase migration history is aligned on local/remote versions `001` through `023` as of 2026-05-17. Check `supabase migration list --linked` before future DB work.
- `supabase db push --yes` should report "Remote database is up to date" immediately after the current `023_analysis_jobs.sql` migration.
- `npm run check:prod-health` checks Railway `/health` and a Supabase REST read for `normalization_stats`.
