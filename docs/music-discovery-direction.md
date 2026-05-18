# Music Discovery Direction

Last updated: 2026-05-17

## Direction

Beattrack should become a focused music discovery tool:

> Find lesser-known songs that truly feel like a track you already love.

This is narrower than "music recommendation" and stronger than "similarity search".

The product should feel less like a technical tool and more like a careful digging assistant for electronic music listeners.

★ ʕ ᵔᴥᵔ ʔ Erklaerbaer
In simple words: Beattrack should not just say "this is similar". It should help someone find the kind of track they would be excited to send to a friend because it feels connected, but is not the obvious answer.

## Critical Finding

The strongest direction is:

- Similar enough to be trusted.
- Fresh enough to feel like discovery.
- Not crowded by duplicates, edits, remixes, or the same obvious artist.
- Clear enough that a new user understands the main flow immediately.

The risky version of this direction would be:

- Over-optimizing for obscure tracks and losing relevance.
- Adding more modes before the main recommendation list earns trust.
- Growing the catalog faster than metadata and duplicate quality can keep up.
- Treating offline similarity scores as proof of user satisfaction.

## Primary User

The primary user is an electronic music explorer.

They may be a listener, collector, DJ, playlist maker, or producer, but the shared need is:

> I have one track I care about. Show me nearby tracks I probably would not have found through normal platform recommendations.

This keeps the target practical without locking Beattrack into only DJs or only casual listeners.

## Main Job-To-Be-Done

When I love a track, I want to find less obvious tracks with a similar feeling, so I can keep exploring without getting trapped in generic recommendations or duplicate versions.

## Product Principles

1. The first screen asks for one seed track.
2. The first result list must earn trust before advanced modes compete for attention.
3. Results should be ranked by discovery value, not only raw similarity.
4. A "bad" result should be easy to classify: wrong energy, wrong genre, duplicate version, too obvious, bad metadata, or other.
5. Saved discoveries and history matter because discovery has memory. A good find is only useful if the user can return to it.

## Ranking Principles

The ranking target should evolve from:

```text
sonic_similarity
```

to:

```text
discovery_score =
  sonic_similarity
  - duplicate_or_version_penalty
  - obviousness_penalty
  - energy_drift_penalty
  + freshness_bonus
```

This is not a final formula. It is the product intent translated into ranking language.

Current live behavior:

- `/similar` now applies a conservative discovery score after late fusion and before dedup/MMR.
- The score keeps sonic similarity as the anchor.
- Same-artist results, same-base-title versions, and extremely close results receive small penalties so they do not dominate the top of the list.
- The penalties are intentionally small: a much stronger sonic match can still rank first.

Practical signals:

- `sonic_similarity`: current MusiCNN/MERT/handcrafted fusion.
- `duplicate_or_version_penalty`: same title base, remix/edit/mixed variants, same artist-title clusters.
- `obviousness_penalty`: same artist, highly repeated known result, too-close version.
- `energy_drift_penalty`: BPM, rhythm, intensity, and focus mismatch.
- `freshness_bonus`: less obvious but still close candidate.

## UI Principles

The main path should be:

1. "Which track do you want to dig from?"
2. User enters a URL or searches a catalog track.
3. Beattrack returns a discovery list.
4. Each result carries a small reason label.
5. User can save, continue digging, or mark why a result missed.

Secondary modes:

- Blend, Vibe, Journey, DJ Mode, and Playlist Builder should remain available.
- They should appear after the user has seen useful recommendations, not as equal first-screen choices.

## Research Check

Online research supports this direction, with nuance.

- Spotify Research describes music discovery as personal and goal-dependent. Their user research found that listeners use discovery recommendations differently depending on whether they want immediate listening or exploration. Source: [Spotify Research, "Understanding and Evaluating User Satisfaction with Music Discovery"](https://research.atspotify.com/publications/understanding-and-evaluating-user-satisfaction-with-music-discovery/).
- Music recommender research repeatedly warns that accuracy alone is not enough. Novelty, diversity, and serendipity matter for satisfaction, but they must stay useful. Source: [Current challenges and visions in music recommender systems research](https://link.springer.com/article/10.1007/s13735-018-0154-2).
- Recent engagement research on music recommendations points in the same direction: beyond-accuracy qualities such as diversity, novelty, and serendipity can matter for long-term engagement. Source: [Beyond accuracy measures: the effect of diversity, novelty and serendipity in recommender systems on user engagement](https://ideas.repec.org/a/spr/elcore/v25y2025i3d10.1007_s10660-024-09813-w.html).
- Broader recommender-system research frames this as a multi-objective problem. Relevance, novelty, diversity, coverage, and popularity bias need to be balanced rather than maximized separately. Source: [A survey on multi-objective recommender systems](https://pmc.ncbi.nlm.nih.gov/articles/PMC10073543/).
- Product-market-fit writing is less domain-specific, but it supports the operational point: retention cohorts are a stronger signal than initial excitement. Source: [Twilio, "Measuring product-market fit"](https://www.twilio.com/en-us/resource-center/measuring-product-market-fit).

## Critical Adjustments After Research

The phrase "unbekanntere Songs" should not mean "obscure at any cost".

Better product wording:

> Less obvious songs that still feel right.

Why this matters:

- Too much similarity feels stale.
- Too much novelty feels random.
- Good discovery lives in the middle: familiar enough to trust, surprising enough to feel valuable.

## Six-Week Plan

### Week 1: Direction And Baseline

- Update product copy and docs around "less obvious songs that still feel right".
- Define success metrics: repeat searches, saved results, negative feedback reasons, share/export intent.
- Keep URL/search as the main seed path; keep upload available but secondary.

### Week 2: Discovery Evaluation Set

- Expand the golden query set from 10 to at least 50 curated Electronic seeds.
- Add `known_bad`, `too_obvious`, and `duplicate_version` notes.
- Record current baseline results before changing ranking.

### Week 3: Discovery Score Prototype

- Add a read-only scoring comparison in `eval_similarity.py`.
- Test duplicate/version penalties.
- Test same-artist and same-title-base penalties.
- Test BPM/intensity drift penalties.

### Week 4: Results UI

- Present results as a discovery list, not just a technical similarity list.
- Add small reason labels such as "same energy", "similar texture", "less obvious", or "possible version duplicate".
- Keep advanced controls secondary.

### Week 5: Feedback Loop

- Build a report over feedback reason tags.
- Use `wrong_energy`, `duplicate_version`, and `too_obvious` to choose ranking fixes.
- Review the top failing seeds weekly.

### Week 6: Retention And Memory

- Add save/history emphasis for discovered tracks.
- Test whether users return to previous searches.
- Add shareable discovery lists only if save/history shows value.

## Non-Goals

- Do not make DJ Mode the main product path during this cycle.
- Do not chase catalog size before reducing duplicate and metadata noise.
- Do not add accounts before save/history has proven useful.
- Do not treat a higher offline similarity score as enough evidence.
- Do not optimize for obscure tracks without checking user-perceived relevance.

## Open Questions

- What popularity or "obviousness" signal is available from Deezer or internal behavior?
- Should "less obvious" mean lower platform popularity, not same artist, not already shown often, or user-specific novelty?
- Should Beattrack expose a novelty slider, or keep that control implicit at first?
- Which subgenres suffer most from energy drift?
- Which result labels actually help users trust the system?
