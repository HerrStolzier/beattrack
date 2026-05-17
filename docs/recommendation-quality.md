# Recommendation Quality

Last updated: 2026-05-17

## Goal

Recommendation quality should become measurable enough that discovery-oriented ranking changes can be compared before and after.

Beattrack recommendations are subjective, but they should still be evaluated with repeatable examples. The goal is not to replace listening judgment. The goal is to make changes less random.

The product direction is now more specific:

> Find less obvious songs that still feel right next to a track the user already loves.

That means ranking quality is not only "nearest neighbor accuracy". It also includes freshness, duplicate avoidance, energy consistency, and perceived discovery value.

## Current Ranking Model

The current backend combines:

- MusiCNN 200-dimensional learned embeddings.
- Optional MERT 768-dimensional embeddings for re-ranking.
- 44-dimensional handcrafted audio features.
- Remix/version deduplication.
- MMR diversity to avoid overly similar result lists.
- Optional focus modes: timbre, harmony, rhythm, brightness, intensity.
- Feedback-learned genre focus weights where available.

## Golden Query Set

The first golden query set lives at:

```text
apps/api/scripts/fixtures/similarity_queries.json
```

Each query contains:

- `artist`
- `title`
- `label`
- `expected_traits`
- `avoid_traits`

This is intentionally small at first. It should grow only with examples that are useful for judging sonic behavior.

## How To Run

Without database access, inspect the fixture:

```bash
cd apps/api
.venv/bin/python scripts/eval_similarity.py --fixture-summary
```

With Supabase env vars available, run a read-only evaluation:

```bash
cd apps/api
.venv/bin/python scripts/eval_similarity.py --limit 10
```

To compare fusion-weight candidates without changing production behavior:

```bash
cd apps/api
.venv/bin/python scripts/eval_similarity.py --limit 5 --strategies balanced,acoustic,embedding
```

Required env vars:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`

In production-like evaluation, `SUPABASE_ANON_KEY` may need the service role value if RLS blocks required reads.

## What To Look For

For each query:

- Do the top 3 results share the intended energy?
- Are there obvious duplicates/remixes crowding the list?
- Are results too genre-literal but not sonically close?
- Are MERT-backed results better than fallback results?
- Does a focus mode improve the intended trait or make results worse?
- Are the results less obvious without becoming random?
- Would a music explorer plausibly save or continue from at least one result?

## Initial Baseline Observation

Run on 2026-05-17 with `--limit 3`:

- 9 of 10 query songs were found in the current catalog.
- `ARTBAT - Return to Oz` was missing.
- Some queries returned plausible same-lane neighbors.
- Some queries showed energy/BPM drift, especially ambient, liquid drum and bass, electro, and downtempo examples.
- Duplicate/version pressure is visible for tracks such as `Bicep - Glue` and `Peggy Gou - It Makes You Forget`.

Practical meaning: the engine is useful enough to evaluate, but it needs a quality loop. The first targets should be duplicate/version handling, BPM/energy consistency, and subgenre-sensitive evaluation.

## Next Improvements

1. Expand from 10 to at least 30 curated Electronic queries.
2. Add internal notes for known-good and known-bad neighbors.
3. Store evaluation snapshots before changing ranking weights.
4. Use feedback reason tags in reporting: `wrong_energy`, `wrong_genre`, `duplicate_version`, `too_obvious`, `bad_metadata`, `other`.
5. Compare default fusion weights against at least two alternatives.
6. Add a discovery-score comparison that tests duplicate/version, obviousness, and energy drift penalties.

## Feedback Reason Tags

Negative result feedback now stores a short reason tag in `feedback.reason_tag`.

This is intentionally simple. A user can still say "Passt nicht", but the app now asks why. That turns a vague downvote into a signal the ranking work can use later.

The database change lives in:

```text
supabase/migrations/024_feedback_reason_tags.sql
```

## Fusion Weight Candidates

Production still uses `balanced` by default.

The evaluation helper can compare three strategies:

- `balanced`: current behavior, MusiCNN-led with MERT and handcrafted as supporting signals.
- `acoustic`: gives handcrafted and MERT slightly more influence, useful when energy, brightness, or rhythm drift is too visible.
- `embedding`: gives MusiCNN more influence, useful when handcrafted traits over-constrain results.

This keeps ranking experiments read-only until there is enough evidence to change the live default.

## Research Notes

External research supports evaluating beyond raw accuracy:

- Spotify Research found that music discovery satisfaction depends on user goals and that discovery behavior differs between immediate listening and exploration.
- Music recommender literature warns that perceived novelty, diversity, and serendipity are subjective and do not always match simple offline metrics.
- Recent engagement research suggests diversity, novelty, and serendipity can matter for longer-term engagement, but they must be balanced with relevance.

Practical implication for Beattrack:

Do not optimize for "unknown" as a standalone goal. Optimize for "less obvious, still right".

See `docs/music-discovery-direction.md` for the fuller source-backed direction.
