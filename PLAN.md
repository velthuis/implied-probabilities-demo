# PLAN.md

The working plan for the demo app. Agents read and update this file, so a new session can pick up
where the last one stopped.

## Current goal
Show the risk-neutral distribution of the S&P 500 implied by Cboe SPX quotes, with checks.

## Decisions so far
- 2026-10-19: Breeden-Litzenberger on a smoothed smile (Malz 2014), not a mixture of lognormals.
- 2026-10-19: Read Cboe's file exactly as downloaded; no extrapolation beyond quoted strikes.
- 2026-10-19: Automatic smoothing: the least that passes the validity checks.
- 2026-10-20: Data is the Oct 19, 2026 Cboe download (the Apr 27, 2022 file was removed on Oct 21).
- 2026-10-20: The distribution comes in closed form from the smile. No bucket table: it would show
  how a later assignment is done.
- 2026-10-21: "Ask the market": the chance of ending below or above any level, next to Black-Scholes.
- 2026-10-21: A fear slider (power utility) shows the real-world distribution the prices imply.

## Next steps
1. Before each term, download a new Cboe file and make it the default.

## Open questions
- Check Cboe's terms of use before keeping the quotes files in a public repository.
