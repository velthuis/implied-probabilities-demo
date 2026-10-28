# Implied probability calculator

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/velthuis/implied-probabilities-demo)

What do option prices imply about where the S&P 500 will be at an expiration date? This
Streamlit app reads SPX option quotes in the layout of Cboe's download, applies
**Breeden-Litzenberger** to a smoothed volatility smile, and compares the **risk-neutral
distribution** with the single lognormal behind Black-Scholes. It opens on **pseudo data**:
made-up quotes that look like real SPX quotes. Upload your own Cboe download to use market data.

It is a teaching demo for MSF 8615 Derivatives at Villanova University, built with an AI coding
agent to show the project workflow: plan → small steps with tests → independent checks →
adversarial review → app → deploy.

## Try it
1. Click **Open in GitHub Codespaces** above (or **Code → Codespaces → Create codespace on main**).
   The first build takes a few minutes.
2. In the terminal: `pytest` (30 tests should pass), then `streamlit run app.py`.
3. In the app, **ask the market**: how likely is a fall of 30% or more, or the index above 10,000?
   Then set the smoothing to "none" and watch the distribution.
4. To keep your changes, commit them: GitHub then creates a **fork** (your own copy) under your
   account. Or click **Fork** at the top of this page first.

If Codespaces don't open on your network, run the app on your own computer:
[`docs/local-setup.md`](docs/local-setup.md) has the steps.

To run it locally once Python is set up:
```
pip install -r requirements.txt
pytest
streamlit run app.py
```

## Inputs and outputs
- **Input:** a quotes file in the layout of Cboe's delayed-quotes download, `spx_quotedata.csv`
  (see Data below). The app reads the index level and quote date from the file and lists its
  expirations; it starts at the one closest to a year away. It opens on the pseudo data file, and
  you can upload a real download.
- **Outputs:**
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
**The default file is pseudo data, not market data.** `data/spx_pseudo_quotes_2026-10-19.csv` is
written by `data/make_pseudo_quotes.py` (`python data/make_pseudo_quotes.py` makes the same file
again). The script prices one SPX expiration (Dec 17, 2027, quoted "Oct 19, 2026") with Black's
formula and these made-up inputs:

| Input | Value |
|---|---|
| Index level | 7,600.00 |
| Risk-free rate | 4.5%, continuously compounded |
| Dividend yield | 1.2%, continuously compounded (forward 7,897.00) |
| Volatility smile | SVI (Gatheral 2004): a = −0.37, b = 0.56, ρ = 0.45, m = 0.63, σ = 0.78, with a skew like the SPX smile's |
| Strikes | 145, from 400 to 12,000, spaced the way Cboe lists a long-dated series |
| Bid and ask | A spread that grows with the price (wider in the money), a little random noise, rounded to Cboe's ticks (0.05 below 3.00, 0.10 above) |

The spreads and tick rounding make the quotes noisy the way real ones are, so the app has to
smooth them. Because the inputs are known, the tests can check the app against them.

The file has the same layout as Cboe's download: two header lines with the index level ("Last:")
and the quote date ("Date:"), then one row per expiration and strike with the call columns, the
strike, and the put columns (`Expiration Date, Calls, Last Sale, Net, Bid, Ask, Volume, IV, Delta,
Gamma, Open Interest, Strike, Puts, Last Sale, ...`). Its IV columns hold the smile it was priced
with.

To use market data: on cboe.com, open the delayed quotes for SPX, show the option chain for the
expirations you want with all strikes, and download the CSV. Upload `spx_quotedata.csv` in the
app without opening or re-saving it in Excel (Excel can change number and date formats). The file
can hold many expirations, SPX (monthly, settled at the open) and SPXW (weekly, settled at the
close); the app lists them separately.

SPX options trade on Cboe. CME's S&P 500 options are options on E-mini futures, a different
contract and file layout.

## Method
**Breeden and Litzenberger (1978)** showed that option prices across strikes imply a probability
distribution for the index at expiration. Raw quotes are too noisy to use directly, so the app
smooths first ("smoothed implied volatility smile": Shimko 1993; Bliss and Panigirtzoglou 2002;
Malz 2014):

1. **Forward and discount factor** from put-call parity, c − p = df (F − K), by weighted
   regression on the ten strikes nearest the index with two-sided call and put quotes.
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
mixture of two lognormals (Bahra 1997), the method an earlier version of this demo used.

## Results on the pseudo data
**Index 7,600; expiration Dec 17, 2027 (424 days).** Forward 7,897 and r = 4.51% from put-call
parity (the generator used 7,897.00 and 4.50%); automatic smoothing 0.01; 100% of 145 quotes priced
inside the spread; volatility at the forward 16.8%.

| Move of at least | −10% | −20% | −30% | −40% | +10% | +20% | +30% | +40% |
|---|---|---|---|---|---|---|---|---|
| Implied by the quotes | 18.8% | 10.5% | 6.1% | 3.7% | 42.2% | 18.3% | 5.2% | 1.2% |
| Black-Scholes | 24.1% | 8.8% | 1.8% | 0.2% | 34.3% | 18.8% | 9.2% | 4.1% |

With a fear level of 2, the real-world chance of a 20% fall is 3.8%, and the expected return
above the risk-free rate is 5.3% a year.

## Tests (`pytest`, 30 tests)
| Test | Checked against |
|---|---|
| Reading the file | Values typed from the file: index 7,600.00 on Oct 19, 2026 and the 7,000 row |
| Reader on a multi-expiration file | SPX vs. SPXW roots and two expirations, built by hand; a broken row raises an error |
| Black's formula and implied vol | Hull Ch. 15 example (c = 4.76, p = 0.81), inverted back to 20% |
| Forward and rate from the file | Put-call parity on the rounded quotes gives back the generator's forward (within 1 point) and rate (within 0.05 points) |
| Implied vols | The file's implied-vol column (the generator's smile), within 1 vol point |
| Volatility width of a quote | Half spread ÷ vega, with vega from a finite difference |
| Put-call parity | Recovers F and df from Black-Scholes prices with unequal call and put spreads |
| Quotes without a bid | Left out, by hand |
| Fit diagnostics | Hand-worked case: errors ±1, ±3 with half-spread 2 → 50% inside, RMS √5 |
| Flat smile | Gives scipy's lognormal (cumulative and density) |
| Two-peaked distribution | Prices from a mixture of two lognormals; cumulative probabilities match scipy within 0.5 points |
| Tails | Model-free put and call spreads from the quotes, within 1 point |
| Validity | No negative density; the density, integrated numerically, matches the cumulative probabilities; ≥ 90% inside spread |
| Validity checks | A hand-made bad distribution is flagged |
| Ask the market | A flat smile gives scipy's lognormal; below and above add up to 1; a bound beyond the quoted strikes |
| Real world vs. risk-neutral | On paper, power utility shifts a lognormal's log-mean by γσ²T: scipy's shifted lognormal and a premium of γσ² a year; no fear gives the market's distribution |
| Automatic smoothing; default expiration | Picks 0.01 on the pseudo data; picks the series nearest one year with 20+ strikes |
| Guards (not independent) | No smoothing → negative probabilities; heavy smoothing → misses quotes and breaks the CDF; bad inputs raise errors |
| App smoke tests | The app runs on the pseudo data (100%; forward 7,897); Ask the market shows 10.5% for a 20% fall and 18.3% for a 20% rise, and a bound beyond the quotes; the fear slider gives 3.8% and 5.3% a year at 2, and the market's distribution at 0 (10.4%: it leaves out the 0.09% below the lowest strike); the tail table hides when a fit is invalid |
| `test_pricing.py` | Black-Scholes tests from the course template |

## Limitations
- The default file is pseudo data: its probabilities illustrate the method and say nothing about
  the market. Upload a Cboe download for real ones.
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
- Bahra, B. (1997). Implied risk-neutral probability density functions from option prices:
  theory and application. Bank of England Working Paper 66.
- Bliss, R. and N. Panigirtzoglou (2002). Testing the stability of implied probability density
  functions. *Journal of Banking & Finance* 26(2–3), 381–422.
- Bliss, R. and N. Panigirtzoglou (2004). Option-implied risk aversion estimates. *Journal of
  Finance* 59(1), 407–446.
- Breeden, D. and R. Litzenberger (1978). Prices of state-contingent claims implicit in option
  prices. *Journal of Business* 51(4), 621–651.
- Gatheral, J. (2004). A parsimonious arbitrage-free implied volatility parameterization with
  application to the valuation of volatility derivatives. Presentation at Global Derivatives &
  Risk Management, Madrid.
- Malz, A. (2014). A simple and reliable way to compute option-based risk-neutral distributions.
  Federal Reserve Bank of New York Staff Report 677.
- Shimko, D. (1993). Bounds of probability. *Risk* 6(4), 33–37.
- Federal Reserve Bank of Minneapolis. [Current and historical market-based probabilities](https://www.minneapolisfed.org/banking/current-and-historical-market--based-probabilities):
  option-implied probabilities for the S&P 500, interest rates, exchange rates and commodities,
  from a variation of Shimko (1993). Its horizons differ from the app's expiration.

## Files in this repository
| File | What it is for |
|---|---|
| `app.py` | The Streamlit page: inputs, charts and captions, no formulas |
| `bl.py` | Cboe reader, Black's formula, parity forward, implied vols, smoothing spline, Breeden-Litzenberger, validity checks |
| `pricing.py` | Black-Scholes, from the course template |
| `tests/` | The checks listed above |
| `data/` | The pseudo quotes file and `make_pseudo_quotes.py`, the script that writes it |
| `AI_LOG.md` | How AI was used, the critic's findings and the fixes |
| `AGENTS.md` | Standing rules the coding agent reads every session |
| `PLAN.md` | The agent's working notes: goal and decisions so far |
| `RUBRIC.md` | The course rubric for the app project |
| `.github/agents/` | Two review agents: `critic` (adversarial, read-only) and `examiner` (practice questions against `RUBRIC.md`) |
| `.agents/skills/` | `check-the-numbers`: how the agent adds a test for every number |
| `docs/` | Guides: [coding agents](docs/agent-setup.md), [Streamlit](docs/streamlit.md), [git as a team](docs/git-and-teamwork.md), [local setup](docs/local-setup.md), [demo script](docs/demo-script.md) |
| `exercise/` | **Catch the AI**: a short exercise with a planted error (`pytest exercise`) |

## For MSF 8615 students
Your team's project does **not** start here: create it from the course template
([velthuis/derivatives-app-template](https://github.com/velthuis/derivatives-app-template) →
**Use this template**). The options payoff demo is in its own repository,
[velthuis/options-payoff-demo](https://github.com/velthuis/options-payoff-demo). In a later
assignment you will estimate this kind of distribution yourself, from the raw quotes.
