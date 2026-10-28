# Demo script

The prompts behind this app, in order. The goal is to show the loop (plan → approve → build →
test → independent check → review), not typing speed. In class, prompt 1 (the plan) runs live,
then the demo switches to the finished app in this repository. Prompts 2–4 are for trying at
home; there is no saved copy of each intermediate step.

## In class: 5–7 minutes
| Step | What to show | Time |
|---|---|---|
| Prompt 1 live, in plan mode | The agent reads AGENTS.md and proposes files, tests and checks; edit the plan and ask "what would make these numbers wrong?" | 2–3 min |
| The finished app | `streamlit run app.py`: **Ask the market** (a class guess first: how likely is a 20% fall by Dec 2027?), the smile, the distribution vs. Black-Scholes; then set the smoothing to "none" | 2–3 min |
| The evidence | `pytest` (30 passed) and two rows of the critic review in `AI_LOG.md` | 1–2 min |
| Optional: prompt 3 live | Only if ahead of time; the agent writes and runs the checks | +3–5 min |

Agent replies take 30–90 seconds. Talk through the spec while the plan is written.

Everything runs in a **Codespace** (VS Code in the browser, opened from github.com). The
github.com page alone cannot run `pytest` or the app.

## 0. Setup
- Create a repository from the course template, open it in a Codespace, and run `pytest` once
  (the first build takes a few minutes). Upload `data/spx_pseudo_quotes_2026-10-19.csv` into its
  `data/` folder so the agent has a file to plan around. Prompt 1 runs there.
- Open a second Codespace on this repository (the finished app), run `pytest` and start
  `streamlit run app.py`, so you can switch to it without waiting.
- In Copilot Chat, open the agent menu below the chat box and check that `critic` and `examiner`
  are listed. If not, reload the window (Ctrl+Shift+P → "Developer: Reload Window").
- Codespaces stop after 30 idle minutes by default. Raise the idle timeout at
  github.com/settings/codespaces, or reopen both from github.com/codespaces shortly before you
  start.
- Any agent from `docs/agent-setup.md` works. Each has a built-in plan mode (Shift+Tab or `/plan`
  in the CLIs, `/plan` or Plan in Copilot).

## 1. The spec, written by you (README, 1 min)
"Question: what distribution for the S&P 500 at an expiration date do option prices imply?
Input: an SPX quotes file in Cboe's download layout. Output: the implied distribution and tail
probabilities next to Black-Scholes, and checks that the distribution is valid.
Method: Breeden-Litzenberger on a smoothed volatility smile (Malz 2014)."

## 2. Plan first: prompt 1 (plan mode, or "don't write code yet")
> Read AGENTS.md and README.md. Propose a plan for a Breeden-Litzenberger implied-distribution
> calculator that reads the Cboe-format quotes file in data/: which functions go in bl.py, which tests will
> show the numbers are right, and what app.py will display. Do not write code yet.

Point out: you edit the plan before approving it. Ask "what would make these numbers wrong?"
(A wrong forward; noise in the quotes, which the density magnifies; reading probabilities
beyond the last strike.)

## 3. Build the core with tests: prompt 2
> Implement step 1 of the plan in bl.py: read the Cboe file, get the forward from put-call
> parity, compute implied vols of out-of-the-money mid-quotes, fit a smoothing spline through
> them weighted by the bid-ask spread, and apply Breeden-Litzenberger. Test that the reader
> returns the index level and the 7,000 row from the file, and that Black's formula matches
> Hull's example (c = 4.76, p = 0.81). Run pytest.

Point out: approving each terminal command vs. auto-approve; reading the diff.

## 4. Check against something computed a different way: prompt 3
> Add tests that compare with calculations done another way: a flat smile must give scipy's
> lognormal; prices from a two-peaked distribution must give back its probabilities; and the
> snapshot's tail probabilities must match put and call spreads computed from the quotes (within
> one percentage point).

Point out: a test that uses the same function on both sides cannot fail.

## 5. The interface: prompt 4
> Update app.py: pick an expiration from the file, a smoothing setting with an automatic
> default, the smile with the smoothed curve, the distribution against Black-Scholes, a table of
> tail probabilities for 10–40% moves, and validity checks. Hide the results when a check fails.
> Generate every caption from the numbers. Then run streamlit.

Point out: set the smoothing to "none". The smile looks the same, but the distribution turns
into spikes with negative probabilities: the density depends on the curve's curvature, which
turns tiny wiggles in the quotes into spikes.

## 6. Adversarial check (if time allows)
Open a new chat, pick the `critic` agent, and ask: "Review this app and its tests. Try to make
the numbers wrong." Log what it finds in AI_LOG.md. The real entries from Oct 19 show why: the
critic ran the app on a live download of 60 expirations, and the fixed smoothing failed on 49 of
them.

## 7. Ship it
Commit and push (a green check from the tests workflow), then deploy on share.streamlit.io.
