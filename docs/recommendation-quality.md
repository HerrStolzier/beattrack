# Recommendation Quality

Last updated: 2026-05-19

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

The reusable ranking helpers live in:

```text
apps/api/app/services/similarity.py
```

The `/similar` route imports those helpers and keeps the HTTP/database flow in:

```text
apps/api/app/routes/similar.py
```

Practical meaning: ranking experiments and evaluation scripts can now use the
same scoring helpers without importing the FastAPI route module. That makes
future changes easier to test and reduces the chance that API wiring and
ranking behavior get mixed together.

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
- `known_bad`
- `too_obvious`
- `duplicate_risks`
- `discovery_intent`

This is intentionally curated rather than exhaustive. It should grow only with examples that are useful for judging sonic behavior.

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

For a faster smoke check over only the first few curated seeds:

```bash
cd apps/api
.venv/bin/python scripts/eval_similarity.py --query-limit 3 --limit 5
```

To compare fusion-weight candidates without changing production behavior:

```bash
cd apps/api
.venv/bin/python scripts/eval_similarity.py --limit 5 --strategies balanced,acoustic,embedding
```

To compare raw similarity with the conservative discovery score:

```bash
cd apps/api
.venv/bin/python scripts/eval_similarity.py --limit 5 --score-mode both
```

To save a compact JSON snapshot for before/after comparison:

```bash
cd apps/api
.venv/bin/python scripts/eval_similarity.py --query-limit 5 --limit 5 --score-mode both --snapshot-out /tmp/beattrack-eval.json
```

To compare two saved evaluation snapshots:

```bash
cd apps/api
.venv/bin/python scripts/compare_eval_snapshots.py /tmp/before.json /tmp/after.json
```

To inspect negative feedback reason tags:

```bash
cd apps/api
.venv/bin/python scripts/report_feedback_reasons.py --limit 1000
```

For automation or saved reports:

```bash
cd apps/api
.venv/bin/python scripts/report_feedback_reasons.py --limit 1000 --format json
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

1. Add known-good neighbors after listening review.
2. Store evaluation snapshots before changing ranking weights.
3. Use feedback reason tags in reporting: `wrong_energy`, `wrong_genre`, `duplicate_version`, `too_obvious`, `bad_metadata`, `other`.
4. Compare default fusion weights against at least two alternatives.
5. Compare BPM drift warnings against listening notes before adding live energy drift penalties.

## Live Discovery Score

The production `/similar` route now applies a small discovery-score adjustment after late fusion and before dedup/MMR.

In plain language: Beattrack still starts with "does this sound close?", but it gently pushes down results that are likely to feel too obvious, such as the same artist, the same base title, or an almost identical neighbor.

The score currently stores the original fused value as `sonic_similarity` internally, then returns the adjusted score as `similarity`. It also keeps internal `discovery_penalty_reasons` so evaluation output can explain whether a candidate was pushed down for `same_artist`, `same_title`, or `too_close`.

Current penalties:

- Same artist: small penalty.
- Same base title: stronger version/duplicate penalty.
- Extremely high sonic similarity: small saturation penalty, because very-near neighbors are often edits, versions, or obvious catalog neighbors.

This is deliberately conservative. It should improve the first result list without turning discovery into random novelty.

The evaluation helper can now print raw and discovery-scored rankings from the same candidate pool via `--score-mode both`. It also prints a short `Rank changes` summary so obvious demotions and fresh-result promotions are easier to inspect. When comparing both modes, it flags top-result BPM differences of 12 BPM or more as `BPM drift warnings`; these are review notes only and do not change production ranking. It also prints a `Discovery penalty summary` showing how many visible results were penalized and how large the total, average, and maximum penalty were. Use `--snapshot-out` to persist a compact JSON snapshot with query metadata, fixture review notes, scores, rank changes, BPM warnings, discovery-penalty summaries, summary counts, and a top-level `review_summary` with penalty-reason and penalty-strength counts. Use `scripts/compare_eval_snapshots.py` to compare those review-summary counts before and after ranking changes.

The fixture now contains 31 curated Electronic seeds with discovery intent notes, too-obvious examples, duplicate/version risks, and known-bad result patterns. In practice, this is the first safety check before tuning penalties: the same input list should reveal whether same-artist, same-title, too-close, or high-BPM-drift results move down without breaking the sonic fit of the top results.

## Evaluation Run: 2026-05-19

Command:

```bash
cd apps/api
.venv/bin/python scripts/eval_similarity.py --query-limit 5 --limit 5 --score-mode both --snapshot-out /tmp/beattrack-eval-discovery.json
```

Result:

- Found 4 of 5 query songs.
- `ARTBAT - Return to Oz` was still missing from the catalog sample.
- Snapshot written to `/tmp/beattrack-eval-discovery.json`.
- `penalized_result_count`: 20.
- `penalty_reason_counts`: `too_close=20`.
- `rank_change_count`: 5.
- `bpm_drift_warning_count`: 2.
- `total_discovery_penalty`: about 0.481.
- `max_discovery_penalty`: about 0.029.

Interpretation:

The current discovery score is conservative and mostly acts as a "too-near
neighbor" softener. That looks safe, but it is not yet a complete discovery
quality mechanism. The Peggy Gou query shows the most useful current behavior:
a same-artist/same-title near-duplicate drops out of the visible top 5, while
nearby house/disco-leaning alternatives move up.

The run also shows that BPM drift remains a real review signal. For the Ricardo
Villalobos query, the top result was about 19 BPM away and another visible
result was about 15 BPM away. This is not enough evidence to add a live BPM
penalty yet, but it is enough to keep BPM/energy drift as the next listening
review topic.

Decision:

Keep the live discovery score unchanged for now. Do not make larger penalty or
fusion-weight changes from this small run alone. The next ranking decision
should compare a larger query sample and include listening notes for cases where
`too_close` demotion or BPM drift changes the visible top results.

## Feedback Reason Tags

Negative result feedback now stores a short reason tag in `feedback.reason_tag`.

This is intentionally simple. A user can still say "Passt nicht", but the app now asks why. That turns a vague downvote into a signal the ranking work can use later.

The read-only helper `scripts/report_feedback_reasons.py` summarizes recent negative feedback by reason tag and can print either text or JSON. It also includes a suggested ranking check for each reason, such as reviewing BPM drift for `wrong_energy` or base-title deduplication for `duplicate_version`. These suggestions are review prompts, not automatic ranking changes. This is the first lightweight bridge from collected feedback to ranking work: if `wrong_energy`, `duplicate_version`, or `too_obvious` dominates, the next ranking experiment should target that failure mode first.

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
