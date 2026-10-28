# PLAN.md

The working plan for the app. Agents read and update this file, so a new session can pick up
where the last one stopped.

## Current goal
Show the risk-neutral distribution of the S&P 500 implied by SPX option quotes, with checks.

## Decisions so far
- 2026-10-19: Breeden-Litzenberger on a smoothed smile (Malz 2014), not a mixture of lognormals.
- 2026-10-19: Read Cboe's file exactly as downloaded; no extrapolation beyond quoted strikes.
- 2026-10-19: Automatic smoothing: the least that passes the validity checks.
- 2026-10-20: The distribution comes in closed form from the smile.
- 2026-10-21: "Ask the market": the chance of ending below or above any level, next to Black-Scholes.
- 2026-10-21: A fear slider (power utility) shows the real-world distribution the prices imply.
- 2026-10-28: The default data is pseudo data from `data/make_pseudo_quotes.py`, in Cboe's layout;
  users can upload a real Cboe download.
