# Implied probability calculator (MSF 8615 demo)

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/velthuis/implied-probabilities-demo)

What do option prices imply about where the S&P 500 will be at an expiration date? This
Streamlit app reads Cboe's SPX option quotes **exactly as you download them**, applies
**Breeden-Litzenberger** to a smoothed volatility smile, and compares the **risk-neutral
distribution** with the single lognormal behind Black-Scholes.

## Try it
1. Click **Open in GitHub Codespaces** above (or **Code → Codespaces → Create codespace on main**).
   GitHub copies the repository into a Codespace for you; the first build takes a few minutes and
   uses your free Codespace hours.
2. In the terminal: `pytest` (29 tests should pass), then `streamlit run app.py`.
3. In the app, **ask the market**: how likely is a fall of 30% or more, or the index above 10,000?
   Then set the smoothing to "none" and watch the distribution.
   `exercise/` has the Catch the AI exercise from the first class (`pytest exercise`).
4. Want to keep your changes? Commit them: GitHub then makes a **fork** (your own copy) under your
   account automatically. Or click **Fork** at the top of this page first. This repository stays
   unchanged.
5. Working on your own laptop instead? `git clone https://github.com/velthuis/implied-probabilities-demo.git`
   (needs Git and Python 3.12).

**Options class:** `options/` has a payoff app an agent wrote earlier (`streamlit run options/app.py`,
`pytest options`) and a Colab starter notebook. See `options/README.md`.

Your team's project does **not** start here: create it from the course template
(github.com/velthuis/derivatives-app-template → **Use this template**).

Built for the Oct 20, 2026 class as a demo of the app-project workflow: template → plan → small
steps with tests → independent checks → adversarial review → app → deploy. In a later
assignment you will estimate this kind of distribution yourself, from the raw quotes.

## Inputs and outputs
- Input: `spx_quotedata.csv` from Cboe's delayed quotes (see Data below). The app reads the
  index level and quote date from the file and lists its expirations; it starts at the one
  closest to a year away. It opens on a download from Oct 19, 2026, and you can upload your own.
- Outputs:
  - **Ask the market:** the chance that the S&P 500 ends below or above any level or % move at
    expiration, next to Black-Scholes, shaded on the distribution chart;
  - **Why "risk-neutral"?** A slider for how much investors fear losses turns the market's
    distribution into the real-world one those prices imply, with the real-world chance of a 20%
    fall and the expected return above the risk-free rate (power utility, Bliss and
    Panigirtzoglou 2004);
  - the smile: each quote's implied volatility and the smoothed curve;
  - the distribution at expiration next to Black-Scholes, over the quoted strikes only;
  - tail probabilities for falls and rises of 10% to 40%;
  - fit diagnostics: share of quotes priced inside the bid-ask spread (in-sample), RMS error,
    and two validity checks (no negative probabilities; cumulative probabilities between 0 and 1).

## Data
| File | Source | Saved | Can it be public? |
|---|---|---|---|
| `spx_quotedata_2026-10-19.csv` (the app's default) | Cboe delayed quotes for SPX (`spx_quotedata.csv`), downloaded by the instructor from cboe.com/delayed_quotes/spx/quote_table, one expiration (Dec 17, 2027), not edited | Oct 19, 2026, 11:40 PM EDT (after the close; the index level is the 4:00 PM close) | Check Cboe's terms of use before making the repository public |

The file is used exactly as Cboe saves it: two header lines with the index level ("Last:") and the
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
**Breeden and Litzenberger (1978)** showed that option prices across strikes imply a probability
distribution for the index at expiration. Raw quotes are too noisy to use directly, so we smooth
first ("smoothed implied volatility smile": Shimko 1993; Bliss and Panigirtzoglou 2002; Malz 2014):

1. **Forward and discount factor** from put-call parity, c − p = df (F − K), weighted regression on
   the ten strikes nearest the index with two-sided call and put quotes.
2. **Implied volatilities** of out-of-the-money mid-quotes (puts below F, calls above), and the
   width of each quote's half spread in volatility terms (half spread ÷ vega).
3. **A quartic smoothing spline** of volatility against ln(K/F), weighted by 1 / that width.
   Quartic, so its curvature has no kinks.
4. **Automatic smoothing:** the least smoothing on a grid (0.01 to 10) whose distribution is
   valid, following Malz (2014).
5. **The distribution in closed form** from Black's formula and the curve: at each strike, the
   smile's level σ, slope σ′ and curvature σ″ give

       P(S_T ≤ K) = N(−d₂) + K φ(d₂) √T σ′
       f(K) = φ(d₂) [1/(Kσ√T) + 2 d₁ σ′/σ + K√T d₁ d₂ σ′²/σ + K√T σ″]

   with d₁, d₂ from Black's formula at σ(K). A flat smile gives back Black-Scholes; the slope and
   curvature are what move the distribution away from the lognormal. Nothing is extrapolated
   beyond the lowest and highest quoted strikes.

Bliss and Panigirtzoglou (2002) found this smoothed-smile approach more stable than fitting a
mix of two lognormals (Bahra 1997), the method an earlier version of this demo used.

## Results on the saved file
**Default: Oct 19, 2026 (index 7,690.73); expiration Dec 17, 2027 (424 days).** Forward 8,080;
r = 5.06% from put-call parity (the 1-year Treasury yield was 4.46% on Oct 16); automatic
smoothing 0.01; 100% of 145 quotes priced inside the spread; volatility at the forward 16.7%.
Falls of 10/20/30/40% or more: 18.2/10.6/6.0/3.5% (Black-Scholes 22.1/7.8/1.5/0.1%).
Rises: 46.2/19.7/6.4/1.7% (Black-Scholes 36.5/20.4/10.2/4.6%). The file was saved at 11:40 PM
EDT, after the close; its index level is the 4:00 PM close.

## Tests (`pytest`, 29 tests)
| Test | Checked against |
|---|---|
| Reading the raw file | Values typed from the file: index 7,690.73 on Oct 19, 2026 and the 7,000 row |
| Reader on a multi-expiration file | SPX vs. SPXW roots and two expirations, built by hand; a broken row raises an error |
| Black's formula and implied vol | Hull Ch. 15 example (c = 4.76, p = 0.81), inverted back to 20% |
| Implied vols | Cboe's own implied-vol column in the file, within 1 vol point |
| Volatility width of a quote | Half spread ÷ vega, with vega from a finite difference |
| Put-call parity | Recovers F and df from Black-Scholes prices with unequal call and put spreads |
| Quotes without a bid | Left out, by hand |
| Fit diagnostics | Hand-worked case: errors ±1, ±3 with half-spread 2 → 50% inside, RMS √5 |
| Flat smile | Gives scipy's lognormal (cumulative and density) |
| Two-peaked distribution | Prices from a mix of two lognormals; cumulative probabilities match scipy within 0.5 points |
| Tails | Model-free put and call spreads from the quotes, within 1 point |
| Validity | No negative density; the density, integrated numerically, matches the cumulative probabilities; ≥ 90% inside spread |
| Validity checks | A hand-made bad distribution is flagged |
| Ask the market | A flat smile gives scipy's lognormal; below and above add up to 1; a bound beyond the quoted strikes |
| Real world vs. risk-neutral | On paper, power utility shifts a lognormal's log-mean by γσ²T: scipy's shifted lognormal and a premium of γσ² a year; no fear gives the market's distribution |
| Automatic smoothing; default expiration | Picks 0.01 on the saved file; picks the series nearest one year with 20+ strikes |
| Guards (not independent) | No smoothing → negative probabilities; heavy smoothing → misses quotes and breaks the CDF; bad inputs raise errors |
| App smoke tests | The app runs on the saved file (100%; forward 8,080); Ask the market shows 10.6% for a 20% fall and 19.7% for a 20% rise, and a bound beyond the quotes; the fear slider gives 3.8% and 5.3% a year at 2, and the market's 10.6% at 0; the tail table hides when a fit is invalid |
| `test_pricing.py` | The template's Black-Scholes tests |

## How to run
```
pip install -r requirements.txt
pytest
streamlit run app.py
```
`docs/streamlit.md` explains how a Streamlit app works, with notes on this one.

## Limitations
- One quote snapshot, one expiration. Delayed quotes can be stale, especially far from the money.
- Nothing beyond the quoted strikes: the app reports how much probability lies below the lowest
  and above the highest strike, but not its shape.
- The smoothing is a choice. Automatic smoothing picks the least that gives a valid distribution;
  a different rule would move the probabilities a little (try the slider).
- On a live download of all 60 SPX and SPXW expirations (Oct 19, 2026), 59 gave a valid
  distribution; one short-dated weekly did not, and the app says so.
- T counts calendar days to expiration; the probabilities do not depend on that choice, only
  the displayed interest rate does.
- Risk-neutral probabilities mix likelihood with risk premia. They are not forecasts.
- The real-world view is an illustration with one simple model of investors (power utility, one
  fear level for all outcomes), over the quoted strikes only. Real-world probabilities can't be
  read off prices.

## References
- Breeden, D. and R. Litzenberger (1978). Prices of state-contingent claims implicit in option
  prices. *Journal of Business* 51(4), 621–651.
- Shimko, D. (1993). Bounds of probability. *Risk* 6(4), 33–37.
- Bliss, R. and N. Panigirtzoglou (2002). Testing the stability of implied probability density
  functions. *Journal of Banking & Finance* 26(2–3), 381–422.
- Bliss, R. and N. Panigirtzoglou (2004). Option-implied risk aversion estimates. *Journal of
  Finance* 59(1), 407–446.
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

