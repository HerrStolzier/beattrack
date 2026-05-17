# Beattrack Product Direction

Last updated: 2026-05-17

## Primary Promise

Beattrack helps electronic music explorers find less obvious songs that still feel right next to a track they already love.

The main path is:

1. Start from one seed track through search, URL, or upload.
2. Let Beattrack identify or analyze the track.
3. Get a focused discovery list of sonically close but less obvious tracks.
4. Save, continue digging, or mark why a recommendation missed.

## Primary User For The Next Cycle

The primary user is an electronic music explorer who already has one track and wants useful nearby tracks they probably would not have found through normal platform recommendations.

This user cares about:

- Sound and energy fit.
- Less obvious discoveries, not only the nearest duplicate.
- Avoiding weak metadata matches, remixes, edits, and repeated versions.
- Fast exploration without needing to understand embeddings or audio analysis.
- Saving or collecting discoveries before they disappear.

## Main Job-To-Be-Done

When I love a track, I want to find less obvious tracks with a similar feeling, so I can keep exploring without getting trapped in generic recommendations or duplicate versions.

## Product Priorities

1. Make the single-track discovery path unmistakably clear.
2. Improve the quality and explainability of recommendations.
3. Keep secondary modes useful but visually secondary.
4. Turn feedback and bad-match reports into ranking improvements.
5. Keep upload/URL failures understandable and recoverable.

## Secondary Modes

Blend, Vibe, Sonic Journey, DJ Mode, and Playlist Builder are valuable, but they should support the main discovery loop instead of competing with it on the first screen.

Practical meaning:

- URL/upload stays the primary first-screen action.
- Blend/Vibe are discovery tools for users who already understand the app.
- Journey and playlist features become natural next steps after results.

See `docs/music-discovery-direction.md` for the fuller researched direction.

## Non-Goals For The Next 4-6 Weeks

- Do not add unrelated genres before improving Electronic recommendation quality.
- Do not add social features, accounts, or public playlist sharing before save/history proves useful.
- Do not migrate away from pgvector unless measured query latency makes it necessary.
- Do not expand the UI with more modes before making the existing modes clearer.
- Do not chase full catalog size at the cost of noisy data.

## Success Signals

- A new user can understand the main action within a few seconds.
- Similarity results feel less like search results and more like a sonic discovery path.
- Bad results can be tagged with a reason.
- Internal evaluation can compare ranking changes before and after.
- Upload and URL failures tell users whether retrying makes sense.
- Users save, continue, or repeat searches often enough to show retention potential.
