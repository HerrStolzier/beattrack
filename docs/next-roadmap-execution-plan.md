# Next Roadmap Execution Plan

Last updated: 2026-05-19

This plan turns the current roadmap discussion into five concrete execution
steps. It is intentionally small-step: each step should leave the repository in
a reviewable state and avoid production deployment unless explicitly requested.

## 1. Commit Similarity Service Refactor

**Goal**: Finish the behavior-preserving similarity refactor already prepared
locally.

**Scope**:

- `apps/api/app/routes/similar.py`
- `apps/api/app/services/similarity.py`
- `apps/api/scripts/eval_similarity.py`
- `apps/api/tests/test_similarity_logic.py`
- Recommendation-quality documentation

**Acceptance**:

- Route stays focused on HTTP request/response and Supabase flow.
- Ranking helpers live in `app.services.similarity`.
- Evaluation and tests import the shared service directly.
- No live ranking behavior changes.

**Verify**:

```bash
cd apps/api && .venv/bin/python -m pytest tests/test_similarity_logic.py tests/test_routes.py -q
cd apps/api && .venv/bin/python -m pytest tests/test_eval_similarity.py tests/test_compare_eval_snapshots.py -q
cd apps/api && .venv/bin/python -m py_compile app/routes/similar.py app/services/similarity.py scripts/eval_similarity.py
```

## 2. Run Real Recommendation Evaluation

**Goal**: Use real Supabase data to judge whether the discovery score helps
with "less obvious, but still fitting" results.

**Scope**:

- `apps/api/scripts/eval_similarity.py`
- `apps/api/scripts/compare_eval_snapshots.py`
- `docs/recommendation-quality.md`

**Acceptance**:

- Run `--score-mode both` against real catalog data.
- Save a snapshot or document a blocker if Supabase env vars/RLS prevent the
  run.
- Summarize penalty reasons, rank changes, and BPM drift warnings.

**Verify**:

```bash
cd apps/api && .venv/bin/python scripts/eval_similarity.py --query-limit 5 --limit 5 --score-mode both --snapshot-out /tmp/beattrack-eval-discovery.json
```

## 3. Decide Ranking Next Step From Evidence

**Goal**: Make a documented recommendation, not a blind tuning change.

**Scope**:

- `docs/recommendation-quality.md`
- Optional tiny ranking fix only if evaluation clearly proves it

**Acceptance**:

- State whether the current discovery score looks plausible, too weak, too
  strong, or needs listening review.
- Stop before bigger weighting or penalty changes.

## 4. Make Worker Logic More Import-Safe

**Goal**: Reduce the amount of business logic living directly in
`app/workers/__init__.py`.

**Scope**:

- `apps/api/app/workers/__init__.py`
- `apps/api/app/workers/analysis.py`
- `apps/api/app/workers/ingest_tasks.py`
- Existing analyze/worker tests

**Acceptance**:

- Procrastinate registration remains in `__init__.py`.
- Analysis and ingest task bodies are importable without registering tasks.
- Existing task names stay unchanged.

**Verify**:

```bash
cd apps/api && .venv/bin/python -m pytest tests/test_analyze.py -q
```

## 5. Make The Next Small Frontend Maintainability Cut

**Goal**: Improve the biggest frontend state hook without changing UI behavior.

**Scope**:

- `apps/web/app/hooks/useAnalyzeState.ts`
- New focused helper/hook only if it keeps the public return shape stable
- Existing AnalyzeView/UrlInput tests

**Acceptance**:

- Public `useAnalyzeState` API remains stable for `AnalyzeView`.
- One clear responsibility moves out of the main hook.
- Existing tests pass.

**Verify**:

```bash
cd apps/web && bun run test --run AnalyzeView UrlInput
```

## Stop Conditions

- Stop before production deployment.
- Stop before migrations.
- Stop before large live ranking changes without evaluation evidence.
- Stop if Supabase env vars, RLS, or missing real data prevent evaluation.
- Stop if a refactor would silently change public behavior.
