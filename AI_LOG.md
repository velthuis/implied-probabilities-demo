# AI log

Three records in one file: how you used AI, what the critic found, and your examiner practice. Add
rows as you go; the rubric (criterion 5) looks for this file.

## 1. AI use
One row per meaningful use, as the syllabus requires. It also shows which parts you need to be able
to explain at the demo.

This backup version was prepared on Oct 19, 2026 with Claude (Cowork) as the coding agent, following
the same steps as the live demo in `docs/demo-script.md`. The instructor reviewed the output.

| Date | Who | Tool and model | What we asked | What we kept or changed | How we checked it |
|---|---|---|---|---|---|
| 2026-10-19 | Instructor + agent | Claude (Cowork) | A first version that read probabilities straight off the raw quotes | Replaced: that is a later assignment's method | — |
| 2026-10-19 | Instructor + agent | Claude (Cowork) | A mixture of lognormals (Bahra 1997; Melick and Thomas 1997) | Replaced: too complicated to explain; Bliss and Panigirtzoglou (2002) found the smoothed-smile method more stable | Its critic review is summarized in section 2 |
| 2026-10-19 | Instructor + agent | Claude (Cowork) | Breeden-Litzenberger on a smoothed smile (Malz 2014), reading the raw Cboe file | Kept `bl.py`; the first saved file was rebuilt from a course workbook | Hull example; scipy lognormal; two-peaked distribution; option spreads from the quotes |
| 2026-10-19 | Instructor + agent | Claude (Cowork) | Which spline? | Cubic splines left kinks in the density at their knots; switched to quartic | Plotted the densities side by side |
| 2026-10-19 | Instructor + agent | Claude (Cowork) | How much smoothing? | A fixed 1/3 moved the 10% rise by 1.2 points; the tail test caught it. Then a fixed 0.01 failed on live data (critic). Now automatic: the least smoothing that passes the validity checks | `test_tails_agree_with_option_spreads_on_the_snapshot`; 59 of 60 live expirations valid |
| 2026-10-19 | Independent reviewer | Claude subagent, fresh session | Critique the app and the tests; try a live download | Eleven findings; all fixed (see section 2) | Six planted bugs the first tests missed: five now fail a test |
| 2026-10-19 | Instructor + agent | Claude (Cowork) | An in-class exercise with a planted error (`exercise/`), on the stylized CIP exam question | A CIP forward that compounds annually although its docstring says continuously, with an equal-rates test and a test that checks the code against itself | Ran it: both tests pass; the exam answer 1.0345 fails (1.0330); after the fix the exam test passes and the self-check fails |
| 2026-10-20 | Instructor + agent | Claude (Cowork) | Use a new Cboe download (Oct 19, 2026) as the default file | Added `data/spx_quotedata_2026-10-19.csv` unedited; the 2022 file stayed in the sidebar (removed Oct 21) | Reader test typed from the file; tails within 1 point of put and call spreads; validity checks; app smoke test (29 tests) |
| 2026-10-20 | Instructor + agent | Claude (Cowork) | Fewer files for students | Merged the review and examiner logs into this file, moved the data notes into the README and the guides into `docs/` | All references updated; 29 tests pass |
| 2026-10-20 | Instructor + agent | Claude (Cowork) | Make sure the demo doesn't show how a later assignment is done | Removed the bucket table and its download; the distribution now comes in closed form from the smile's level, slope and curvature; added a check against Cboe's own implied vols | Same tail probabilities on both files; leaving out any one term of the formula fails a test; 30 tests pass |
| 2026-10-21 | Instructor + agent | Claude (Cowork) | A more interesting app: "Ask the market"; drop the 2022 file | `ask_market` in `bl.py` and an Ask the market section with shading on the chart; the 2022 file and its tests removed | A flat smile gives scipy's lognormal; the app shows 10.6% for a 20% fall, matching the tail table; 27 tests pass |
| 2026-10-21 | Instructor + agent | Claude (Cowork) | Show visually what risk-neutral probabilities are | A fear slider: `real_world()` reweights the market's density by S^γ (Bliss and Panigirtzoglou 2004) and the app shows both curves, the real-world chance of a 20% fall and the implied equity premium | On paper a lognormal's log-mean shifts by γσ²T: scipy agrees, premium γσ²; at γ = 2 the app shows 3.8% and 5.3% a year; 29 tests pass |
| 2026-10-21 | Instructor + agent | Claude (Cowork) | A backup for the options class: a payoff app from the class prompt, and a Colab starter notebook | `options/` with its own tests, run with `pytest options` | Its 4 tests pass |
| 2026-10-22 | Instructor + agent | Claude (Cowork) | Link to the Minneapolis Fed's market-based probabilities | A caption under Ask the market, plus the method notes and README references | Checked the page: options-based, a variation of Shimko (1993); app tests pass |

## 2. Critic review
Run the critic agent in a **new chat session**, before each milestone and before the demo. Log every
finding, including the ones you decide not to fix, and say why. Check each finding yourself: a
second agent's opinion is not proof.

**Current version: Breeden-Litzenberger on a smoothed smile**

| Date | Reviewer (agent or person) | Finding | Severity | What we did | Test added |
|---|---|---|---|---|---|
| 2026-10-19 | Independent Claude reviewer, fresh session | The fixed default smoothing (0.01) fit the noise in real data: on a live Cboe download of 60 SPX/SPXW expirations, only 11 came out clean, while the app still said "100% inside bid-ask". The help text ("keeps the curve well inside the spreads while removing the noise") was true only on the saved snapshot | High | Automatic smoothing: the least smoothing on a grid that passes the validity checks (Malz 2014 chooses his step the same way). Parity now uses the ten nearest strikes, weighted by spread. On the same live file, 59 of 60 expirations are valid; the app says so for the last one | `test_automatic_smoothing_picks_the_least_that_passes` |
| 2026-10-19 | Same | Crash: on one live expiration the smoothed vol went below zero and Streamlit showed a traceback | High | `bl_distribution` raises a readable error; every calculation runs inside the app's error handling | `test_app_runs_on_the_snapshot` (smoke test) |
| 2026-10-19 | Same | Results were shown when the checks failed, and the two warnings could contradict each other ("increase" and "reduce" the smoothing) | Medium | One message that names the failed checks; the tail table and summary sentence are hidden | `test_no_smoothing_hides_the_tail_table` |
| 2026-10-19 | Same | The default expiration was the last in the file (a 2031 series with 35 quotes) | Medium | Starts at the series closest to one year with at least 20 quoted strikes | `test_default_expiration_is_nearest_one_year_with_enough_strikes` |
| 2026-10-19 | Same | Six planted bugs passed the tests (parity on asks or bids, a full-spread vol width, zero bids kept, no CDF > 1 check, wrong density end values); the parity test had bid = ask; the mean test had a built-in 19-point bias | Medium | New tests with unequal call and put spreads, zero bids, a hand-checked vol width, a bad distribution, and density-vs-cumulative consistency; the biased mean test removed. Five of the six bugs now fail a test; the density end values (two grid points, display only) are not tested | 7 new tests, including two app smoke tests (25 in total) |
| 2026-10-19 | Same | Stale docs (README, data/README, AGENTS.md still described the mixture app; AGENTS.md even forbade smile smoothing) | Medium | Rewritten | None |
| 2026-10-19 | Same | Parity gave implausible rates on short weeklies (−15.7% for a 1-day series) | Low | Weighted regression on the nearest strikes; a discount factor outside 0.5–1.05 is refused; the caption shows days, not 0.00 years | In `test_parity_recovers_forward_and_discount_factor` |
| 2026-10-19 | Same | "At-the-money" vol fell back to the median vol when the forward was outside the quoted strikes | Low | Now an error: the forward must lie inside the quoted strikes | None |
| 2026-10-19 | Same | The reader accepted rows with the wrong number of columns (an unquoted 4,800 became strike 4) | Low | Any row whose column count differs from the header raises an error | In `test_rejects_bad_inputs` |
| 2026-10-19 | Same | A tiny negative density triggered a warning that read "0.0%" | Low | Threshold 0.1% of probability, shown with two decimals | None |

**Earlier version: mixture of three lognormals (replaced Oct 19, 2026)**

The first version fitted a mix of lognormals (Bahra 1997; Melick and Thomas 1997). Its review
found nine problems, including two High ones: extrapolation shown as if it were measured (with
strikes at 95–105%, the fit looked perfect while the 30% fall moved from 10.5% to 14.0%), and a
hard-coded caption that was wrong at the 10% level. Four planted bugs passed its first tests.
We fixed all of them, then replaced the method with Breeden-Litzenberger, which is simpler to
explain and more stable (Bliss and Panigirtzoglou 2002).

## 3. Examiner practice
Before the demo, run the examiner agent with `RUBRIC.md` and paste its report here. Practice scores
do not determine grades.

- Date and commit reviewed:
- Team members (3-5), GitHub usernames, and own-commit links:
- Evidence inspected and evidence it could not see:

| Criterion | Level | Maximum | Awarded | Evidence and next step |
|---|---|---|---|---|
| 1. Finance | | 25 | | |
| 2. Verification | | 25 | | |
| 3. Working app | | 10 | | |
| 4. Data and privacy | | 10 | | |
| 5. Agent supervision | | 10 | | |
| 6. Group presentation and demo (practice) | | 15 | | |

| Student | GitHub username | Own-account commit link | Criterion 7 (5 or 0) |
|---|---|---|---|
| | | | |

Use the level conversion in `RUBRIC.md`. Mark evidence the examiner could not see "not assessed",
and report a complete total only when every criterion is assessed.
