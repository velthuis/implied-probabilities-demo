"""What do option prices imply about the S&P 500 at an expiration date?

Streamlit interface for Breeden-Litzenberger on a smoothed smile (bl.py).
Run with:  streamlit run app.py
"""
from math import log

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from bl import (add_implied_vols, ask_market, auto_smile, equity_premium, real_world, bl_distribution, default_series, density_checks,
                fit_report, fit_smile, lognormal_cdf, one_series, otm_quotes, parity_forward, prob_below,
                read_cboe_csv, series_list, smile_prices)

SNAPSHOTS = {
    "Saved Cboe download: SPX, Oct 19, 2026": "data/spx_quotedata_2026-10-19.csv",
}
SMOOTHING = ["automatic", 0.0, 0.001, 0.01, 0.1, 1.0, 10.0]

st.set_page_config(page_title="Implied probability calculator", page_icon="📊", layout="wide")
st.title("What do option prices imply about the S&P 500?")
st.caption(
    "Breeden-Litzenberger: option prices across strikes imply a probability distribution for the index "
    "at expiration. Probabilities are **risk-neutral**: they combine the market's view of "
    "how likely each outcome is with how much investors care about it. They are not a forecast."
)

# ---------- Inputs ----------
with st.sidebar:
    st.header("Data")
    source = st.radio("Option quotes", list(SNAPSHOTS) + ["Upload a Cboe quotes CSV"])
    try:
        if source.startswith("Upload"):
            upload = st.file_uploader("spx_quotedata.csv from cboe.com (delayed quotes → Download CSV)", type="csv")
            if upload is None:
                st.info("Upload the file exactly as Cboe saves it.")
                st.stop()
            chain, spot, quote_date = read_cboe_csv(upload)
        else:
            chain, spot, quote_date = read_cboe_csv(SNAPSHOTS[source])
    except ValueError as err:
        st.error(f"Could not read the file: {err}")
        st.stop()
    st.write(f"Index level **{spot:,.2f}** on **{quote_date:%b %d, %Y}** (from the file)")
    later = [s for s in series_list(chain) if s[0] > quote_date]
    try:
        start = later.index(default_series(chain, quote_date))
    except ValueError as err:
        st.error(f"No usable expiration: {err}")
        st.stop()
    expiration, root = st.selectbox("Expiration", later, index=start,
                                    format_func=lambda s: f"{s[0]:%b %d, %Y} ({s[1]}, {(s[0] - quote_date).days} days)",
                                    help="Starts at the expiration closest to one year with at least 20 quoted strikes.")
    days = (expiration - quote_date).days
    T = days / 365

    st.header("Method")
    smoothing = st.select_slider(
        "Smoothing of the volatility curve", options=SMOOTHING, value="automatic",
        format_func=lambda s: s if isinstance(s, str) else ("none" if s == 0 else f"{s:g}"),
        help="Automatic: the least smoothing that gives a valid distribution (no negative probabilities, "
             "cumulative probabilities between 0 and 1). Try 'none': the curve passes through every quote "
             "and their noise makes probabilities negative. Try 10: a calm curve that misses most quotes.")

# ---------- Calculation ----------
one = one_series(chain, expiration, root)
try:
    F, df = parity_forward(one, spot)
    quotes = add_implied_vols(otm_quotes(one, F), F, T, df)
    if smoothing == "automatic":
        used, smile, dist, checks = auto_smile(quotes, F, T, df)
    else:
        used = smoothing
        smile = fit_smile(quotes, F, smoothing)
        dist = bl_distribution(smile, T, df)
        checks = density_checks(dist)
    if not smile.k_lo <= F <= smile.k_hi:
        raise ValueError("the forward lies outside the quoted strikes")
    report = fit_report(smile_prices(smile, quotes, T, df), quotes)
    sigma = float(smile.vol(F))
except ValueError as err:
    st.error(f"Could not compute a distribution for this expiration: {err}. Pick another expiration or "
             "another smoothing level.")
    st.stop()
r = -log(df) / T

# ---------- Results ----------
c1, c2, c3 = st.columns([1, 1, 3])
c1.metric("Fit inside bid-ask", f"{report['inside_spread']:.0%}",
          help="In-sample: the share of the quotes used whose price on the smooth curve lies between bid and ask.")
c1.caption(f"{report['n']} out-of-the-money options, strikes {smile.k_lo:,.0f}–{smile.k_hi:,.0f}; "
           f"RMS pricing error {report['rmse']:.2f} points; smoothing {used:g}"
           + (" (automatic)" if smoothing == "automatic" else ""))
c2.metric("Forward from put-call parity", f"{F:,.0f}")
c2.caption(f"r = {r:.2%} per year; T = {days} days; Black-Scholes comparison at the implied volatility "
           f"at the forward, {sigma:.1%}")

rows = []
for x in (0.10, 0.20, 0.30, 0.40):
    down, up = prob_below(dist, (1 - x) * spot), prob_below(dist, (1 + x) * spot)
    rows.append({"Move": f"{x:.0%}+",
                 "Fall, implied": down,
                 "Fall, B-S": lognormal_cdf(F, sigma, (1 - x) * spot, T),
                 "Rise, implied": None if up is None else 1 - up,
                 "Rise, B-S": 1 - lognormal_cdf(F, sigma, (1 + x) * spot, T)})
tails = pd.DataFrame(rows)
fmt = lambda v: "beyond quotes" if v is None or pd.isna(v) else f"{v:.1%}"
if checks["valid"]:
    c3.dataframe(tails.style.format({k: fmt for k in tails.columns[1:]}), hide_index=True, width="stretch")
    c3.caption("Probability that the index is at least this far below or above its level on the quote date, at "
               "expiration. 'Beyond quotes': outside the quoted strikes, where this app does not extrapolate.")
else:
    problems = []
    if checks["negative_mass"] >= 1e-3:
        problems.append(f"the density is negative over {checks['negative_mass']:.2%} of probability (the curve "
                        "follows the noise in the quotes)")
    if checks["cdf_outside"] >= 1e-3:
        problems.append(f"cumulative probabilities go {checks['cdf_outside']:.2%} outside 0 to 1 (the curve's prices "
                        "allow arbitrage)")
    c3.error("Not a valid distribution at this smoothing: " + "; ".join(problems) + ". The tail table is hidden. "
             "Choose 'automatic'.")


def compare(implied, bs, what, size):
    if implied is None or pd.isna(implied):
        return None
    return f"{'more' if implied > bs else 'less'} probability to {what} of {size} or more ({implied:.1%} vs. {bs:.1%})"


parts = [compare(tails.iloc[i][f"{side}, implied"], tails.iloc[i][f"{side}, B-S"], what, size)
         for side, what in (("Fall", "falls"), ("Rise", "rises")) for i, size in ((0, "10%"), (3, "40%"))]
parts = [p for p in parts if p]
summary = ("Compared with Black-Scholes, the market assigns " + "; ".join(parts) + ".") if parts and checks["valid"] else ""

# ---------- Ask the market ----------
st.subheader("Ask the market")
a1, a2, a3 = st.columns([1.1, 1.1, 1.6])
side = a1.radio("Chance that the S&P 500 ends", ["below", "above"], horizontal=True, key="ask_side")
unit = a2.radio("Enter", ["a % move", "an index level"], horizontal=True, key="ask_unit")
if unit == "a % move":
    pct = a3.number_input("Change from the level on the quote date (%)", min_value=-95.0, max_value=300.0,
                          value=-20.0 if side == "below" else 20.0, step=5.0, format="%.1f", key=f"ask_pct_{side}")
    level = spot * (1 + pct / 100)
else:
    level = a3.number_input("S&P 500 level at expiration", min_value=1.0,
                            value=float(round(spot * (0.8 if side == "below" else 1.2), -2)), step=100.0,
                            key=f"ask_level_{side}")
    pct = (level / spot - 1) * 100
if checks["valid"]:
    ans = ask_market(dist, level, side, F, sigma, T)
    p, bs = ans["implied"], ans["bs"]
    shown = f"{ans['bound']} {p:.1%}" if ans["bound"] else f"{p:.1%}"
    b1, b2, b3 = st.columns([1, 1, 2.2])
    b1.metric("Options market", shown)
    b2.metric("Black-Scholes", f"{bs:.1%}")
    odds = f", about 1 in {1 / p:,.0f}" if not ans["bound"] and 0.0005 < p < 0.5 else ""
    beyond = (f" {level:,.0f} lies beyond the quoted strikes ({smile.k_lo:,.0f}–{smile.k_hi:,.0f}), so the app "
              "gives a bound instead of extrapolating.") if ans["bound"] else ""
    b3.markdown(
        f"The options market puts the chance that the S&P 500 ends **{side} {level:,.0f}** ({pct:+.0f}% from "
        f"{spot:,.2f}) on **{expiration:%b %d, %Y}** at **{shown}**{odds}. Black-Scholes, with one volatility "
        f"for every strike, says {bs:.1%}.{beyond}")
    b3.caption("A risk-neutral probability: it also reflects how much investors pay to insure against the "
               "outcome, so it is not a forecast.")
else:
    st.info("Choose 'automatic' smoothing to ask the market: at this smoothing the distribution is not valid.")
st.caption("Compare: the Federal Reserve Bank of Minneapolis publishes [market-based probabilities]"
           "(https://www.minneapolisfed.org/banking/current-and-historical-market--based-probabilities) "
           "for the S&P 500, interest rates, exchange rates and commodities, with a similar method (a variation "
           "of Shimko 1993). Its horizons differ from this expiration, so the numbers won't match exactly.")

left, right = st.columns(2)
with left:
    st.subheader("1. The smile: implied volatility by strike")
    pts = alt.Chart(quotes).mark_circle(size=22, color="#5A6470", opacity=0.8).encode(
        x=alt.X("strike:Q", title="Strike"), y=alt.Y("iv:Q", title="Implied volatility", axis=alt.Axis(format="%")),
        tooltip=["strike", "type", "bid", "ask", alt.Tooltip("iv:Q", format=".2%")])
    bars = alt.Chart(quotes.assign(lo=quotes["iv"] - quotes["iv_err"], hi=quotes["iv"] + quotes["iv_err"])).mark_rule(
        color="#8A949E").encode(x="strike:Q", y="lo:Q", y2="hi:Q")
    curve_k = np.linspace(smile.k_lo, smile.k_hi, 400)
    curve = alt.Chart(pd.DataFrame({"strike": curve_k, "iv": smile.vol(curve_k)})).mark_line(
        color="#C4622D", strokeWidth=3).encode(x="strike:Q", y="iv:Q")
    st.altair_chart((bars + pts + curve).properties(height=330), width="stretch")
    st.caption("Dots: implied volatility of each out-of-the-money mid-quote; gray bars: half the bid-ask spread "
               "in volatility terms. Orange: the smoothed curve. A flat line would mean Black-Scholes holds.")
with right:
    st.subheader("2. The distribution at expiration")
    d = dist.assign(**{"Implied (Breeden-Litzenberger)": dist["pdf"] * 100})
    sd = sigma * np.sqrt(T)
    ln_pdf = np.exp(-0.5 * ((np.log(d["strike"] / F) + 0.5 * sd**2) / sd) ** 2) / (d["strike"] * sd * np.sqrt(2 * np.pi))
    d["Black-Scholes (lognormal)"] = ln_pdf * 100
    long = d.melt("strike", value_vars=["Implied (Breeden-Litzenberger)", "Black-Scholes (lognormal)"],
                  var_name="series", value_name="density")
    lines = alt.Chart(long).mark_line(strokeWidth=2.5).encode(
        x=alt.X("strike:Q", title="S&P 500 level at expiration"),
        y=alt.Y("density:Q", title="Probability per 100 index points", axis=alt.Axis(format="%")),
        color=alt.Color("series:N", title=None,
                        scale=alt.Scale(domain=["Implied (Breeden-Litzenberger)", "Black-Scholes (lognormal)"],
                                        range=["#C4622D", "#5A6470"]), legend=alt.Legend(orient="top-left", labelLimit=300)),
        strokeDash=alt.condition(alt.datum.series == "Black-Scholes (lognormal)", alt.value([6, 4]), alt.value([1, 0])),
        tooltip=[alt.Tooltip("strike:Q", format=",.0f"), alt.Tooltip("density:Q", format=".2%")])
    spot_rule = alt.Chart(pd.DataFrame({"x": [spot]})).mark_rule(color="#2B66B0").encode(x="x:Q")
    layers = lines + spot_rule
    if checks["valid"]:
        picked = d[d["strike"] <= level] if side == "below" else d[d["strike"] >= level]
        shade = alt.Chart(pd.DataFrame({"strike": picked["strike"], "density": picked["pdf"] * 100})).mark_area(
            color="#C4622D", opacity=0.25).encode(x="strike:Q", y="density:Q")
        ask_rule = alt.Chart(pd.DataFrame({"x": [level]})).mark_rule(color="#C4622D", strokeDash=[4, 3]).encode(x="x:Q")
        layers = shade + layers + ask_rule
    st.altair_chart(layers.properties(height=330), width="stretch")
    if checks["valid"]:
        st.caption(f"{summary} Blue line: index level on the quote date. Shaded: the outcome you asked about. "
                   f"The curve covers the quoted strikes only: "
                   f"{checks['below']:.1%} of probability lies below {smile.k_lo:,.0f} and {checks['above']:.1%} "
                   f"above {smile.k_hi:,.0f}.")
    else:
        st.caption("Blue line: index level on the quote date. At this smoothing the curve is not a valid "
                   "probability distribution (see the message above).")

# ---------- 3. Why "risk-neutral"? ----------
st.subheader("3. Why “risk-neutral”? How fear shapes the market’s probabilities")
st.markdown(
    "Option prices are not pure forecasts. Investors pay extra for protection against a crash, so the "
    "market's probabilities put more weight on bad outcomes than investors actually expect. Move the "
    "slider: if investors fear losses this much, what **real-world** chances do these prices imply?")
if checks["valid"]:
    gamma = st.slider("How much investors fear losses (relative risk aversion)", 0.0, 6.0, 2.0, 0.5, key="gamma",
                      help="0: investors don't care about risk, and the real-world chances equal the market's. "
                           "Higher: more fear, so the market's prices overstate the real chance of a fall.")
    real = real_world(dist, gamma)
    rw_below = lambda x: float(np.interp(x, real["strike"], real["cdf"]))
    rn_below = lambda x: prob_below(dist, x)
    f1, f2, f3 = st.columns(3)
    crash = 0.8 * spot
    f1.metric("Fall of 20% or more, real world", f"{rw_below(crash):.1%}")
    f1.caption(f"The market's probability: {rn_below(crash):.1%}")
    if side == "below" and abs(level - crash) < 1:
        f2.caption("Ask the market a different question above, and its real-world chance appears here.")
    elif smile.k_lo <= level <= smile.k_hi:
        rn_q = rn_below(level) if side == "below" else 1 - rn_below(level)
        rw_q = rw_below(level) if side == "below" else 1 - rw_below(level)
        f2.metric(f"Your question: {side} {level:,.0f}, real world", f"{rw_q:.1%}")
        f2.caption(f"The market's probability: {rn_q:.1%}")
    else:
        f2.metric(f"Your question: {side} {level:,.0f}", "beyond quotes")
    f3.metric("Expected return above the risk-free rate", f"{equity_premium(dist, real, T):.1%} a year",
              help="What these prices and this fear level imply investors expect to earn on the index, "
                   "above the risk-free rate. With no fear it is zero: in the risk-neutral world every "
                   "asset earns the risk-free rate, and the index is expected to end at the forward price.")
    both = pd.DataFrame({"strike": dist["strike"], "Market (risk-neutral)": dist["pdf"].clip(lower=0) * 100,
                         "Real world at this fear level": real["pdf"] * 100}).melt(
        "strike", var_name="series", value_name="density")
    fear = alt.Chart(both).mark_line(strokeWidth=2.5).encode(
        x=alt.X("strike:Q", title="S&P 500 level at expiration"),
        y=alt.Y("density:Q", title="Probability per 100 index points", axis=alt.Axis(format="%")),
        color=alt.Color("series:N", title=None,
                        scale=alt.Scale(domain=["Market (risk-neutral)", "Real world at this fear level"],
                                        range=["#C4622D", "#2B66B0"]), legend=alt.Legend(orient="top-left", labelLimit=300)),
        tooltip=[alt.Tooltip("strike:Q", format=",.0f"), alt.Tooltip("density:Q", format=".2%")])
    now = alt.Chart(pd.DataFrame({"x": [spot]})).mark_rule(color="#8A949E", strokeDash=[2, 2]).encode(x="x:Q")
    st.altair_chart((fear + now).properties(height=300), width="stretch")
    st.caption("An illustration with one simple model of investors (power utility; Bliss and Panigirtzoglou 2004, "
               "Journal of Finance), over the quoted strikes only. Gray line: index level on the quote date. "
               "Real-world probabilities can't be read off "
               "prices; this shows what the market's numbers would mean at the fear level you pick. At 0 the "
               "two curves are the same.")
else:
    st.info("Choose 'automatic' smoothing first: at this smoothing the distribution is not valid.")

with st.expander("How the calculation works"):
    st.markdown(
        r"""
**Breeden and Litzenberger (1978)** showed that option prices across strikes imply a probability
distribution for the index at expiration. Raw quotes are too noisy to use directly, so we smooth first:

1. **Forward and discount factor** from put-call parity, $c-p = df\,(F-K)$, near the money.
2. **Implied volatilities** of out-of-the-money mid-quotes (puts below the forward, calls above).
3. **A smoothing spline** through the vols against $\ln(K/F)$, weighted by how tight each quote is
   (Bliss and Panigirtzoglou 2002; Malz 2014 uses a similar recipe). It is quartic, so its curvature
   has no kinks. **Automatic** smoothing picks the least smoothing that gives a valid distribution:
   no negative probabilities, and cumulative probabilities between 0 and 1.
4. **The distribution in closed form** from Black's formula and the smooth curve $\sigma(K)$, its
   slope $\sigma'$ and its curvature $\sigma''$, with $d_1, d_2$ from Black's formula at $\sigma(K)$:

$$P(S_T \le K) = N(-d_2) + K\,\varphi(d_2)\sqrt{T}\,\sigma'$$

$$f(K) = \varphi(d_2)\left[\frac{1}{K\sigma\sqrt{T}} + \frac{2 d_1 \sigma'}{\sigma} + \frac{K\sqrt{T}\, d_1 d_2\, \sigma'^2}{\sigma} + K\sqrt{T}\,\sigma''\right]$$

With a flat smile ($\sigma' = \sigma'' = 0$) these are the Black-Scholes probabilities: the smile's
slope and curvature are what move the distribution away from the lognormal.

Nothing is extrapolated beyond the lowest and highest quoted strikes.

References: Breeden and Litzenberger (1978), *Journal of Business*; Shimko (1993), *Risk*;
Bliss and Panigirtzoglou (2002), *Journal of Banking & Finance*; Malz (2014), Federal Reserve Bank of
New York Staff Report 677. The real-world view: Bliss and Panigirtzoglou (2004), *Journal of Finance*.
The Federal Reserve Bank of Minneapolis publishes
[market-based probabilities](https://www.minneapolisfed.org/banking/current-and-historical-market--based-probabilities)
from options with a variation of Shimko (1993).
"""
    )

st.caption(f"Data: {'uploaded Cboe file' if source.startswith('Upload') else 'saved Cboe delayed quotes for SPX'}, "
           f"quoted {quote_date:%b %d, %Y}. "
           "Dividends are reflected in the parity forward. Student demo app, not investment advice.")
