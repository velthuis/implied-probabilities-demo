# Live demo script

Goal: show the loop (plan → approve → build → test → independent check → review), not typing
speed. In class, run **prompt 1 (the plan) live**, then switch to the finished app in this repo.
Prompts 2–4 below are for students to try at home (there is no saved copy of each intermediate
step).

## In class: 5–7 minutes
| Step | What you show | Time |
|---|---|---|
| Prompt 1 live, in plan mode | The agent reads AGENTS.md and proposes files, tests and checks; you edit the plan and ask "what would make these numbers wrong?" | 2–3 min |
| The finished app | `streamlit run app.py`: the smile, the distribution vs. Black-Scholes, the tail table; then set the smoothing to "none" | 1–2 min |
| The evidence | `pytest` (29 passed) and two rows of the critic review in `AI_LOG.md` | 1–2 min |
| Optional: prompt 3 live | Only if you are ahead of time; the agent writes and runs the checks | +3–5 min |

Agent replies take 30–90 seconds. Talk through the spec (slide 9 of the class deck) while the plan
is written. After the demo, students do **Catch the AI** in teams: `exercise/README.md`, 8 minutes.
After the debrief, run the **critic** live on the exercise (slide 15, 2 minutes): new chat (+), pick
`critic` in the agent menu below the chat box, and ask "Review exercise/cip.py and its tests. Try
to make the numbers wrong. Do not edit any file." It should flag the annual compounding and the
test that compares the code with itself.

Everything runs in a **Codespace** (VS Code in the browser, opened from github.com), the same as
students use. The github.com page alone cannot run `pytest` or the app.

## 0. Setup (before class)
- Create a repo from the template, open it in a Codespace, and run `pytest` once (the first
  Codespace build takes a few minutes). Prompt 1 runs here: in that Codespace, upload
  `data/spx_quotedata_2026-10-19.csv` into `data/` so the agent has a file to plan around.
- Open a second Codespace on this demo repo (the finished app), run `pytest` and start
  `streamlit run app.py`, so you can switch to it without waiting.
- In Copilot Chat, open the agent menu below the chat box and check that `critic` and `examiner`
  are listed. If not, reload the window (Ctrl+Shift+P → "Developer: Reload Window"). Rehearse
  the critic once on `exercise/cip.py`, then undo any changes (Source Control → Discard All
  Changes).
- Codespaces stop after 30 idle minutes by default. Raise the idle timeout at
  github.com/settings/codespaces, or reopen both from github.com/codespaces 10 minutes before
  class.
- Use any agent from `docs/agent-setup.md`. Copilot works in the Codespace without a paid plan
  (lower limits); Antigravity CLI, Codex and Claude Code run in its terminal. Every one has a
  built-in plan mode (Shift+Tab or `/plan` in the CLIs, `/plan` or Plan in Copilot).

## 1. Spec: written by you (README, 1 min)
"Question: what distribution for the S&P 500 at an expiration date do option prices imply?
Input: Cboe's SPX quotes file, exactly as downloaded. Output: the implied distribution and tail
probabilities next to Black-Scholes, and checks that the distribution is valid.
Method: Breeden-Litzenberger on a smoothed volatility smile (Malz 2014). Our Project 1
butterflies will check it."

## 2. Plan first: prompt 1, live (plan mode / "don't write code yet")
> Read AGENTS.md and README.md. Propose a plan for a Breeden-Litzenberger implied-distribution
> calculator that reads the raw Cboe file in data/: which functions go in bl.py, which tests will
> show the numbers are right, and what app.py will display. Do not write code yet.

Point out: you edit the plan before approving. Ask "what would make these numbers wrong?"
(A wrong forward; noise in the quotes, which second derivatives magnify; reading probabilities
beyond the last strike.)

## 3. Build the core with tests: prompt 2
> Implement step 1 of the plan in bl.py: read the Cboe file, get the forward from put-call
> parity, compute implied vols of out-of-the-money mid-quotes, fit a smoothing spline through
> them weighted by the bid-ask spread, and apply Breeden-Litzenberger. Test that the reader
> returns the index level and the 4,800 row from the file, and that Black's formula matches
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
into spikes with negative probabilities: second derivatives magnify tiny wiggles. That is what
raw butterflies do in Project 1.

## 5b. Adversarial check (if time allows)
Open a new chat, pick the `critic` agent, and ask: "Review this app and its tests. Try to make
the numbers wrong." Log what it finds in AI_LOG.md (see the real entries from Oct 19: the critic
ran our app on a live download of 60 expirations, and the fixed smoothing failed on 48 of them).

## 6. Ship it
Commit and push (green check from the tests workflow), then deploy on share.streamlit.io.
