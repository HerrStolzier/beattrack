# Release Checklist

Use this before deploying Beattrack changes.

## Before Deploy

1. Check the working tree:

```bash
git status --short
```

Do not mix unrelated user changes, generated data, and release changes in one commit.

2. Run backend checks:

```bash
cd apps/api
.venv/bin/python -m pytest -q
```

3. Run frontend checks when frontend files changed:

```bash
cd apps/web
bun run test
bunx tsc --noEmit
```

4. Check production baseline:

```bash
npm run check:prod-health
```

## Database Changes

1. Inspect migration state:

```bash
supabase migration list
```

2. Apply migrations before deploying code that depends on them:

```bash
supabase db push --yes
```

3. For destructive changes, write an explicit rollback migration. Do not rely on manual dashboard edits.

## Backend Deploy

- Railway root directory: `apps/api`.
- Health endpoint: `/health`.
- After deploy, check Railway logs for import errors, worker errors, and failed health checks.

## Frontend Deploy

- Vercel deploys from `main`.
- Confirm `NEXT_PUBLIC_API_URL` points to the current Railway backend.
- Recheck key flows: search, URL identify, upload analysis, similar results.

## After Deploy

Run:

```bash
npm run check:prod-health
```

For analysis-job issues:

```bash
cd apps/api
.venv/bin/python scripts/analysis_jobs_report.py
```

## Rollback Notes

- Frontend-only issue: revert the frontend commit and redeploy Vercel.
- Backend-only issue: revert the backend commit and redeploy Railway.
- Database issue: apply an explicit rollback migration. Avoid deleting migration history manually.
- Ranking quality issue: restore the previous fusion strategy or weights and compare with `scripts/eval_similarity.py`.
