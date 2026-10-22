"""What do option prices imply about the S&P 500 at an expiration date?

Streamlit interface for Breeden-Litzenberger on a smoothed smile (bl.py).
Run with:  streamlit run app.py
"""
from math import log

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from bl import (add_implied_vols, auto_smile, bl_distribution, bucket_table, default_series, density_checks,
                fit_report, fit_smile, lognormal_cdf, one_series, otm_quotes, parity_forward, prob_below,
                read_cboe_csv, series_list, smile_prices)

SNAPSHOTS = {
    "Saved Cboe download: SPX, Oct 19, 2026": "data/spx_quotedata_2026-10-19.csv",
    "Saved Cboe download: SPX, Apr 27, 2022 (Project 1)": "data/spx_quotedata_2022-04-27.csv",
}
SMOOTHING = ["automatic", 0.0, 0.001, 0.01, 0.1, 1.0, 10.0]

st.set_page_config(page_title="Implied probability calculator", page_icon="📊", layout="wide")
st.title("What do option prices imply about the S&P 500?")
st.caption(
    "Breeden-Litzenberger: the probability density of the index at expiration is the curvature of "
    "call prices across strikes. Probabilities are **risk-neutral**: they combine the market's view of "
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
    st.altair_chart((lines + spot_rule).properties(height=330), width="stretch")
    if checks["valid"]:
        st.caption(f"{summary} Blue line: index level on the quote date. The curve covers the quoted strikes only: "
                   f"{checks['below']:.1%} of probability lies below {smile.k_lo:,.0f} and {checks['above']:.1%} "
                   f"above {smile.k_hi:,.0f}.")
    else:
        st.caption("Blue line: index level on the quote date. At this smoothing the curve is not a valid "
                   "probability distribution (see the message above).")

with st.expander("How the calculation works"):
    st.markdown(
        r"""
**Breeden and Litzenberger (1978).** A call pays $\max(S_T-K,0)$, so its price falls as the strike rises,
and the rate of fall tells you how likely the index is to end above $K$. With discount factor $df$:

$$P(S_T \le K) = 1 + \frac{1}{df}\,\frac{\partial c}{\partial K}, \qquad f(K) = \frac{1}{df}\,\frac{\partial^2 c}{\partial K^2}.$$

A butterfly spread is the second difference of call prices, so Project 1's butterflies measure the same
density from raw quotes. Raw quotes are noisy, and second differences magnify the noise. So we smooth first:

1. **Forward and discount factor** from put-call parity, $c-p = df\,(F-K)$, near the money.
2. **Implied volatilities** of out-of-the-money mid-quotes (puts below the forward, calls above).
3. **A smoothing spline** through the vols against $\ln(K/F)$, weighted by how tight each quote is
   (Bliss and Panigirtzoglou 2002; Malz 2014 uses a similar recipe). It is quartic, so the density
   has no kinks at the spline's knots. **Automatic** smoothing picks the least smoothing that gives
   a valid distribution: no negative probabilities, and cumulative probabilities between 0 and 1.
   Malz chooses his differencing step the same way.
4. **Call prices** from the smooth curve on a 5-point grid, then numerical first and second differences.

Nothing is extrapolated beyond the lowest and highest quoted strikes.

References: Breeden and Litzenberger (1978), *Journal of Business*; Shimko (1993), *Risk*;
Bliss and Panigirtzoglou (2002), *Journal of Banking & Finance*; Malz (2014), Federal Reserve Bank of
New York Staff Report 677.
"""
    )

with st.expander("Bucket probabilities (to compare with Project 1)"):
    h = st.select_slider("Bucket width (points)", options=[50, 100, 200, 400], value=200)
    centers = np.arange(np.ceil(smile.k_lo / h) * h, smile.k_hi, h)
    buckets = bucket_table(dist, centers, h, F_ln=F, s_ln=sigma, T=T)
    st.dataframe(buckets.style.format({"strike": "{:,.0f}", "implied": "{:.2%}", "butterfly": "{:.2%}",
                                       "lognormal": "{:.2%}"}), hide_index=True, width="stretch")
    st.download_button("Download buckets (CSV)", buckets.to_csv(index=False), "implied_buckets.csv", "text/csv")
    st.caption("implied: probability that the index ends within h/2 of the strike. butterfly: what a butterfly "
               "with strike spacing h measures on the smooth curve, (c(K−h) − 2c(K) + c(K+h)) / (df·h), a "
               "triangle-weighted average over K ± h. Compare your Project 1 butterflies with that column. "
               "lognormal: Black-Scholes.")

st.caption(f"Data: {'Cboe delayed quotes for SPX saved Apr 27, 2022, 4:59 PM EDT' if not source.startswith('Upload') else 'uploaded Cboe file'}. "
           "Dividends are reflected in the parity forward. Student demo app, not investment advice.")
