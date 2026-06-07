# Known Errors

## Raw `bun test` Fails With Missing DOM APIs

### Symptom

Frontend tests fail with errors like `ReferenceError: document is not defined`, `window is not defined`, or `vi.mocked is not a function`.

### Ursache

Raw `bun test` uses Bun's test runner and bypasses the project's Vitest/jsdom setup.

### Loesung

Use the project script:

```bash
cd apps/web && bun run test
```

## Next Internal PostCSS Audit Finding

### Symptom

`npm audit --workspaces --omit=dev` reports `node_modules/next/node_modules/postcss <8.5.10`.

### Ursache

Stable Next.js versions currently pin an internal `postcss@8.4.31`. A canary version may contain a newer PostCSS, but using canary only for audit cleanliness is not an acceptable production tradeoff.

### Loesung

Keep stable Next.js, keep top-level PostCSS updated, and re-check when a stable Next.js release ships with internal `postcss >=8.5.10`. Track the decision in `docs/security-remediation-2026-05-20.md`.

## Python Audit Reports Optional Model Dependencies

### Symptom

`pip-audit` reports advisories for `torch` and `transformers`.

### Ursache

These packages belong to the optional MERT/model dependency area. They are not the same issue as the public upload parser dependency.

### Loesung

Do not treat this as blocking the upload-parser fix. Decide separately whether MERT dependencies belong in the production API image or in an isolated model worker.

## Supabase Local Status Fails Without Docker

### Symptom

`supabase status` fails with a Docker daemon connection error.

### Ursache

`supabase status` inspects the local Supabase stack and requires Docker. Remote project access can still work.

### Loesung

For remote migration checks use:

```bash
supabase projects list
supabase migration list
```

Only use `supabase status` when the local Docker-based Supabase stack is actually needed.

## Supabase Migration History Drift

### Symptom

`supabase db push` reports local/remote migration mismatch or tries to apply unexpected migrations.

### Ursache

The remote migration history can drift from local files if SQL was applied manually or migrations were renamed.

### Loesung

Stop before applying more SQL. Run `supabase migration list`, compare local and remote entries, and document the exact mismatch before choosing repair SQL or migration-history cleanup.

## Supabase Advisor Meldet Public Genre Weight Materialized View

### Symptom

Supabase Advisor meldet `materialized_view_in_api` fuer `public.genre_focus_weights`.

### Ursache

`genre_focus_weights` liefert oeffentliche Aggregat-Gewichtungen fuer die Recommendation-API. Das Live-Backend liest Supabase aktuell mit einem echten `anon`-Key; ein Revoke wuerde das Ranking oder den Fallback-Pfad verschlechtern. Direkte Rohdaten-Tabellen, interne Jobs und Reporting-Surfaces muessen getrennt davon geschlossen bleiben.

### Loesung

Nicht pauschal `anon SELECT` entziehen, solange die App diese Aggregate ueber den oeffentlichen API-Pfad braucht. Erlaubt ist nur `anon SELECT`; `authenticated` und `PUBLIC` sollen keine Select-Rechte haben. `feedback_stats` ist dagegen kein oeffentliches App-Surface mehr: `/feedback/stats` ist admin-geschuetzt, nutzt `SUPABASE_SERVICE_ROLE_KEY`, und `anon SELECT` auf `feedback_stats` ist entzogen. Wenn die App spaeter vollstaendig ueber einen Service-Role-Backendpfad liest, kann auch `genre_focus_weights` privat werden.

## Supabase Advisor Meldet Extensions In Public

### Symptom

Supabase Advisor meldet `extension_in_public` fuer `vector` und `pg_trgm`.

### Ursache

Die bestehende Datenbank nutzt `vector`-Typen und Trigram/Vector-Objekte aus dem `public`-Schema. Ein direktes Verschieben der Extensions kann Funktionssignaturen, Typreferenzen, Indexe oder alte Migrationen brechen.

### Loesung

Nicht als Schnellfix verschieben. Dafuer ist eine eigene geplante Migration noetig: Extension-Abhaengigkeiten inventarisieren, Funktionen/Typreferenzen auf das neue Schema umstellen, lokal und live testen, dann erst `alter extension ... set schema ...` anwenden.
