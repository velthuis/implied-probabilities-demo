# Implied probability calculator (MSF 8615 demo)

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/velthuis/implied-probability-demo)

What do option prices imply about where the S&P 500 will be at an expiration date? This
Streamlit app reads Cboe's SPX option quotes **exactly as you download them**, applies
**Breeden-Litzenberger** to a smoothed volatility smile, and compares the **risk-neutral
distribution** with the single lognormal behind Black-Scholes.

## Try it
1. Click **Open in GitHub Codespaces** above (or **Code → Codespaces → Create codespace on main**).
   GitHub copies the repository into a Codespace for you; the first build takes a few minutes and
   uses your free Codespace hours.
2. In the terminal: `pytest` (29 tests should pass), then `streamlit run app.py`.
3. In the app, set the smoothing to "none" and watch the distribution.
   In class we also do **Catch the AI**: `exercise/README.md` (run it with `pytest exercise`).
4. Want to keep your changes? Commit them: GitHub then makes a **fork** (your own copy) under your
   account automatically. Or click **Fork** at the top of this page first. This repository stays
   unchanged.
5. Working on your own laptop instead? `git clone https://github.com/velthuis/implied-probability-demo.git`
   (needs Git and Python 3.12).

Your team's project does **not** start here: create it from the course template
(github.com/velthuis/msf8615-app-template → **Use this template**).

Built for the Oct 20, 2026 class as a demo of the app-project workflow: template → plan → small
steps with tests → independent checks → adversarial review → app → deploy. In Project 1 you
estimate the same distribution from raw quotes with butterfly spreads in Excel, and use your
results to check this app.

## Inputs and outputs
- Input: `spx_quotedata.csv` from Cboe's delayed quotes (see Data below). The app reads the
  index level and quote date from the file and lists its expirations; it starts at the one
  closest to a year away. It opens on a download from Oct 19, 2026; the Apr 27, 2022 file from the
  Project 1 workbook is in the sidebar, and you can upload your own.
- Outputs:
  - the smile: each quote's implied volatility and the smoothed curve;
  - the distribution at expiration next to Black-Scholes, over the quoted strikes only;
  - tail probabilities for falls and rises of 10% to 40%;
  - fit diagnostics: share of quotes priced inside the bid-ask spread (in-sample), RMS error,
    and two validity checks (no negative probabilities; cumulative probabilities between 0 and 1);
  - bucket and butterfly probabilities for any strike spacing h, as a CSV, for Project 1.

## Data
| File | Source | Saved | Can it be public? |
|---|---|---|---|
| `spx_quotedata_2026-10-19.csv` (the app's default) | Cboe delayed quotes for SPX (`spx_quotedata.csv`), downloaded by the instructor from cboe.com/delayed_quotes/spx/quote_table, one expiration (Dec 17, 2027), not edited | Oct 19, 2026, 11:40 PM EDT (after the close; the index level is the 4:00 PM close) | Check Cboe's terms of use before making the repository public |
| `spx_quotedata_2022-04-27.csv` | Cboe delayed quotes for SPX (`spx_quotedata.csv`), rebuilt cell for cell from the Project 1 workbook's `spx_quotedata` sheet in Cboe's CSV layout | Apr 27, 2022, 4:59 PM EDT | Check Cboe's terms of use before making the repository public |

Both files are used exactly as Cboe saves them: two header lines with the index level ("Last:") and the
quote date ("Date:"), then one row per expiration and strike with the call columns, the strike,
and the put columns (`Expiration Date, Calls, Last Sale, Net, Bid, Ask, Volume, IV, Delta, Gamma,
Open Interest, Strike, Puts, Last Sale, ...`).

To use newer data: on cboe.com, open the delayed quotes for SPX, show the option chain for the
expirations you want with all strikes, and download the CSV. Upload `spx_quotedata.csv` in the
app without opening or re-saving it in Excel (Excel can change number and date formats). The file
can hold many expirations, SPX (monthly, settled at the open) and SPXW (weekly, settled at the
close); the app lists them separately.

SPX options trade on Cboe. CME's S&P 500 options are options on E-mini futures, a different
contract and file layout.

## Method
**Breeden and Litzenberger (1978).** With discount factor df and call prices c(K):

    P(S_T ≤ K) = 1 + (1/df) dc/dK          density f(K) = (1/df) d²c/dK²

A butterfly spread is a second difference of call prices, so butterflies measure the same
density from raw quotes, and inherit their noise. So we smooth first ("smoothed implied
volatility smile": Shimko 1993; Bliss and Panigirtzoglou 2002; Malz 2014):

1. **Forward and discount factor** from put-call parity, c − p = df (F − K), weighted regression on
   the ten strikes nearest the index with two-sided call and put quotes.
2. **Implied volatilities** of out-of-the-money mid-quotes (puts below F, calls above), and the
   width of each quote's half spread in volatility terms (half spread ÷ vega).
3. **A quartic smoothing spline** of volatility against ln(K/F), weighted by 1 / that width.
   Quartic, so the density has no kinks at the knots.
4. **Automatic smoothing:** the least smoothing on a grid (0.01 to 10) whose distribution is
   valid. Malz (2014) chooses his differencing step the same way.
5. **Call prices** from the curve on a 5-point grid; numerical first and second differences.
   Nothing is extrapolated beyond the lowest and highest quoted strikes.

Bliss and Panigirtzoglou (2002) found this smoothed-smile approach more stable than fitting a
mix of two lognormals (Bahra 1997), the method an earlier version of this demo used.

## Results on the saved files
**Default: Oct 19, 2026 (index 7,690.73); expiration Dec 17, 2027 (424 days).** Forward 8,080;
r = 5.06% from put-call parity (the 1-year Treasury yield was 4.46% on Oct 16); automatic
smoothing 0.01; 100% of 145 quotes priced inside the spread; volatility at the forward 16.7%.
Falls of 10/20/30/40% or more: 18.2/10.6/6.0/3.5% (Black-Scholes 22.1/7.8/1.5/0.1%).
Rises: 46.2/19.7/6.4/1.7% (Black-Scholes 36.5/20.4/10.2/4.6%). The file was saved at 11:40 PM
EDT, after the close; its index level is the 4:00 PM close.

**Project 1: Apr 27, 2022 (index 4,183.96); expiration Apr 21, 2023.** Forward 4,244; r = 2.58%;
automatic smoothing 0.01; 100% of 120 quotes priced inside the spread.
Falls of 10/20/30/40% or more: 27.0/17.3/10.5/6.4% (Black-Scholes 34.9/18.7/7.3/1.8%).
Rises: 45.1/20.4/5.8/1.6% (Black-Scholes 32.2/20.3/12.1/6.9%).

## Tests (`pytest`, 29 tests)
| Test | Checked against |
|---|---|
| Reading the raw files | Values typed from each file: index 4,183.96 on Apr 27, 2022 and the 4,800 row; 7,690.73 on Oct 19, 2026 and the 7,000 row |
| Reader on a multi-expiration file | SPX vs. SPXW roots and two expirations, built by hand; a broken row raises an error |
| Black's formula and implied vol | Hull Ch. 15 example (c = 4.76, p = 0.81), inverted back to 20% |
| Volatility width of a quote | Half spread ÷ vega, with vega from a finite difference |
| Put-call parity | Recovers F and df from Black-Scholes prices with unequal call and put spreads |
| Quotes without a bid | Left out, by hand |
| Fit diagnostics | Hand-worked case: errors ±1, ±3 with half-spread 2 → 50% inside, RMS √5 |
| Flat smile | Gives scipy's lognormal (cumulative and density) |
| Two-peaked distribution | Prices from a mix of two lognormals; cumulative probabilities match scipy within 0.5 points |
| Buckets and butterflies | Differences of scipy's CDF; a butterfly priced by hand with Black-Scholes |
| Tails (both files) | Model-free put and call spreads from the quotes, within 1 point |
| Validity (both files) | No negative density; density integrates to the cumulative difference; ≥ 90% inside spread |
| Validity checks | A hand-made bad distribution is flagged |
| Automatic smoothing; default expiration | Picks 0.01 on the 2022 file; picks the series nearest one year with 20+ strikes |
| Guards (not independent) | No smoothing → negative probabilities; heavy smoothing → misses quotes and breaks the CDF; bad inputs raise errors |
| App smoke tests | The app runs on both files (100%; forwards 8,080 and 4,244) and hides the tail table when a fit is invalid |
| `test_pricing.py` | The template's Black-Scholes tests |

## How to run
```
pip install -r requirements.txt
pytest
streamlit run app.py
```
`docs/streamlit.md` explains how a Streamlit app works, with notes on this one.

## Limitations
- Two quote snapshots, one expiration each. Delayed quotes can be stale, especially far from the money.
- Nothing beyond the quoted strikes: the app reports how much probability lies below the lowest
  and above the highest strike, but not its shape.
- The smoothing is a choice. Automatic smoothing picks the least that gives a valid distribution;
  a different rule would move the probabilities a little (try the slider).
- On a live download of all 60 SPX and SPXW expirations (Oct 19, 2026), 59 gave a valid
  distribution; one short-dated weekly did not, and the app says so.
- T counts calendar days to expiration; the probabilities do not depend on that choice, only
  the displayed interest rate does.
- Risk-neutral probabilities mix likelihood with risk premia. They are not forecasts.

## References
- Breeden, D. and R. Litzenberger (1978). Prices of state-contingent claims implicit in option
  prices. *Journal of Business* 51(4), 621–651.
- Shimko, D. (1993). Bounds of probability. *Risk* 6(4), 33–37.
- Bliss, R. and N. Panigirtzoglou (2002). Testing the stability of implied probability density
  functions. *Journal of Banking & Finance* 26(2–3), 381–422.
- Malz, A. (2014). A simple and reliable way to compute option-based risk-neutral distributions.
  Federal Reserve Bank of New York Staff Report 677.

## Project objective: explain and verify
The team can explain what the app computes, why the method fits the question, and how each
displayed number was verified, and every member presents part of the group demo. Evidence: `tests/`
and `AI_LOG.md` (AI use, the critic's review, examiner practice against `RUBRIC.md`).

## Files in this repo
| File | Who uses it | What it is for |
|---|---|---|
| `README.md` | You | This page: the question, data, method, checks, limitations and team |
| `AI_LOG.md` | You | How you used AI, the critic's findings and your fixes, and examiner practice |
| `RUBRIC.md` | You read it | How the app is graded |
| `AGENTS.md` | The agent | Standing rules it reads every session. Add a rule when it repeats a mistake |
| `PLAN.md` | The agent | Notes on the current task, so a new session can pick up where the last one stopped |
| `app.py`, `pricing.py`, `tests/`, `data/` | Code | The page, the formulas, the checks, the dated data files |
| `docs/` | You, when needed | Guides: setting up your agent, how Streamlit works, git as a team |

To read a `.md` file with its formatting: on github.com, click it. In a Codespace, right-click it
and choose **Open Preview** (Ctrl+Shift+V).

## Working with agents
`docs/agent-setup.md` explains how to run any of four agents in a Codespace: GitHub Copilot (free for
students), Antigravity CLI, Codex or Claude Code. All of them read `AGENTS.md`, and each has a
built-in plan mode. The team agents in `.github/agents/` each have one job:
`critic` (adversarial, read-only, new session), and `examiner` (practice questions for the group demo, against
`RUBRIC.md`). `docs/git-and-teamwork.md` covers pulling, pushing and merge conflicts.

## AI use
See `AI_LOG.md`, and `docs/demo-script.md` for the prompts used.

## Team size and your own commit
Teams have **3-5 students**. One member creates the repository and invites the other **2-4**.
Every member makes **at least one commit under their own GitHub account** that adds something the
project needs: a formula, a test, a data file and its notes, part of the README, or rows in
`AI_LOG.md`. You decide what; an empty or placeholder file does not count. That commit is worth
**5 points per student** (all or nothing). Check the history together, and never share accounts.
The other **95 points are shared** by the team, and every member presents part of the group
presentation and demo.

