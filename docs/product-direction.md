# Beattrack Product Direction

Last updated: 2026-05-17

## Primary Promise

Beattrack helps electronic music listeners and DJs find the next track that feels sonically connected to a track they already have in mind.

The main path is:

1. Paste a music URL or upload an audio file.
2. Let Beattrack identify or analyze the track.
3. Get a focused list of sonically similar tracks.
4. Continue discovery through focus controls, journey, blend/vibe, or playlist building.

## Primary User For The Next Cycle

The primary user is an electronic music listener or DJ who already has one track and wants useful nearby tracks quickly.

This user cares about:

- Sound and energy fit.
- Avoiding obvious duplicates or weak metadata matches.
- Fast exploration without needing to understand embeddings or audio analysis.
- Exporting or collecting ideas into a playlist-like flow.

## Main Job-To-Be-Done

When I have a track I like, I want to quickly find other tracks that sound compatible, so I can keep listening, build a set, or discover a new direction.

## Product Priorities

1. Make the single-track discovery path unmistakably clear.
2. Improve the quality and explainability of recommendations.
3. Keep secondary modes useful but visually secondary.
4. Turn feedback and bad-match reports into ranking improvements.
5. Keep upload/URL failures understandable and recoverable.

## Secondary Modes

Blend, Vibe, Sonic Journey, and Playlist Builder are valuable, but they should support the main discovery loop instead of competing with it on the first screen.

Practical meaning:

- URL/upload stays the primary first-screen action.
- Blend/Vibe are discovery tools for users who already understand the app.
- Journey and playlist features become natural next steps after results.

## Non-Goals For The Next 4-6 Weeks

- Do not add unrelated genres before improving Electronic recommendation quality.
- Do not add social features, accounts, or public playlist sharing yet.
- Do not migrate away from pgvector unless measured query latency makes it necessary.
- Do not expand the UI with more modes before making the existing modes clearer.
- Do not chase full catalog size at the cost of noisy data.

## Success Signals

- A new user can understand the main action within a few seconds.
- Similarity results feel less like search results and more like a sonic path.
- Bad results can be tagged with a reason.
- Internal evaluation can compare ranking changes before and after.
- Upload and URL failures tell users whether retrying makes sense.
