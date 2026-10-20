"""Risk-neutral distribution from option prices: Breeden-Litzenberger on a smoothed smile.

Breeden and Litzenberger (1978): with discount factor df and call prices c(K),
    P(S_T <= K)  = 1 + (1/df) dc/dK        (cumulative probability)
    density f(K) = (1/df) d2c/dK2           (probability per index point)
Second derivatives of raw quotes are too noisy to use (that is what butterflies measure), so
we follow the "smoothed implied volatility smile" approach (Shimko 1993; Bliss and
Panigirtzoglou 2002; Malz 2014):
  1. turn each out-of-the-money mid-quote into a Black implied volatility,
  2. fit a smoothing spline through the vols, weighted by how tight each quote is,
     smooth enough that the density has no kinks,
  3. turn the smooth curve back into call prices on a fine grid of strikes,
  4. differentiate those prices numerically.
We report nothing beyond the lowest and highest quoted strikes: no extrapolation.

Units: strikes and prices in index points, T in years, volatilities as annual decimals,
df = discount factor e^(-rT).
"""
import csv
import io
import re
from dataclasses import dataclass
from datetime import date, datetime
from math import exp, log, sqrt

import numpy as np
import pandas as pd
from scipy.interpolate import UnivariateSpline
from scipy.optimize import brentq

from pricing import norm_cdf


# ---------- Reading Cboe's delayed-quotes download ----------

def read_cboe_csv(source) -> tuple[pd.DataFrame, float, date]:
    """Read Cboe's delayed-quotes download (spx_quotedata.csv) exactly as saved.

    `source` is a path, or a file-like object with text or bytes. The header lines carry the
    index level ("Last: 4183.96") and the quote date ("Date: April 27, 2022, 4:59 PM EDT").
    Returns (chain, index level, quote date). The chain has one row per series and strike:
    expiration (date), root (SPX, SPXW, ...), strike, call_bid, call_ask, put_bid, put_ask,
    call_oi, put_oi.
    """
    if hasattr(source, "read"):
        raw = source.read()
        text = raw.decode("utf-8-sig") if isinstance(raw, bytes) else raw
    else:
        with open(source, encoding="utf-8-sig") as f:
            text = f.read()
    rows = list(csv.reader(io.StringIO(text)))
    head = next((i for i, r in enumerate(rows) if r and r[0].strip() == "Expiration Date"
                 and "Strike" in [c.strip() for c in r]), None)
    if head is None:
        raise ValueError("not a Cboe quotes file: no header row with 'Expiration Date' and 'Strike'")
    top = "\n".join(text.splitlines()[:head + 2])  # raw header text (a level like 5,000.50 may be unquoted)
    last = re.search(r"Last:\s*(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)", top)
    when = re.search(r"Date:\s*([A-Z][a-z]+ \d{1,2}, \d{4})", top)
    if last is None or when is None:
        raise ValueError("the header lines must include 'Last:' (index level) and 'Date:'")
    spot = float(last.group(1).replace(",", ""))
    quote_date = datetime.strptime(when.group(1), "%B %d, %Y").date()

    h = [c.strip() for c in rows[head]]
    k, c0, p0 = h.index("Strike"), h.index("Calls"), h.index("Puts")
    call = {name: c0 + 1 + h[c0 + 1:k].index(name) for name in ("Bid", "Ask", "Open Interest")}
    put = {name: p0 + 1 + h[p0 + 1:].index(name) for name in ("Bid", "Ask", "Open Interest")}

    def num(x):
        x = x.strip().replace(",", "")
        return float(x) if x not in ("", "-") else 0.0

    out = []
    for n, r in enumerate(rows[head + 1:], start=head + 2):
        if not any(c.strip() for c in r):
            continue
        if len(r) != len(h):
            raise ValueError(f"line {n} has {len(r)} columns; the header has {len(h)} (a number with an "
                             "unquoted thousands separator?)")
        out.append({
            "expiration": datetime.strptime(r[0].strip(), "%a %b %d %Y").date(),
            "root": re.match(r"[A-Z]+", r[c0].strip()).group(0) if r[c0].strip() else "",
            "strike": num(r[k]),
            "call_bid": num(r[call["Bid"]]), "call_ask": num(r[call["Ask"]]),
            "put_bid": num(r[put["Bid"]]), "put_ask": num(r[put["Ask"]]),
            "call_oi": num(r[call["Open Interest"]]), "put_oi": num(r[put["Open Interest"]]),
        })
    if not out:
        raise ValueError("the file has a header but no option rows")
    return pd.DataFrame(out), spot, quote_date


def series_list(chain: pd.DataFrame) -> list[tuple[date, str]]:
    """The (expiration, root) pairs in a chain, sorted by expiration."""
    return sorted(set(zip(chain["expiration"], chain["root"])))


def default_series(chain: pd.DataFrame, quote_date: date, min_strikes: int = 20,
                   target_days: int = 365) -> tuple[date, str]:
    """The series closest to `target_days` after the quote date with at least `min_strikes`
    strikes that have a two-sided call or put quote."""
    best = None
    for e, r in series_list(chain):
        if e <= quote_date:
            continue
        one = one_series(chain, e, r)
        quoted = ((one["call_bid"] > 0) & (one["call_ask"] > one["call_bid"])) | \
                 ((one["put_bid"] > 0) & (one["put_ask"] > one["put_bid"]))
        if quoted.sum() >= min_strikes:
            gap = abs((e - quote_date).days - target_days)
            if best is None or gap < best[0]:
                best = (gap, (e, r))
    if best is None:
        raise ValueError(f"no expiration after {quote_date} has {min_strikes} quoted strikes")
    return best[1]


def one_series(chain: pd.DataFrame, expiration: date, root: str) -> pd.DataFrame:
    sel = chain[(chain["expiration"] == expiration) & (chain["root"] == root)]
    return sel.sort_values("strike").reset_index(drop=True)


# ---------- Black (1976) on the forward ----------

def black_call(F: float, K: float, sigma: float, T: float, df: float) -> float:
    """Black (1976) call on a forward F: df * (F N(d1) - K N(d2))."""
    if F <= 0 or K <= 0 or sigma <= 0 or T <= 0:
        raise ValueError("F, K, sigma and T must be positive")
    sd = sigma * sqrt(T)
    d1 = (log(F / K) + 0.5 * sd**2) / sd
    return df * (F * norm_cdf(d1) - K * norm_cdf(d1 - sd))


def black_put(F: float, K: float, sigma: float, T: float, df: float) -> float:
    """Black (1976) put, from put-call parity on the forward: c - p = df (F - K)."""
    return black_call(F, K, sigma, T, df) - df * (F - K)


def black_vega(F: float, K: float, sigma: float, T: float, df: float) -> float:
    """Change in the Black price per unit of volatility (index points per 1.00 of vol)."""
    sd = sigma * sqrt(T)
    d1 = (log(F / K) + 0.5 * sd**2) / sd
    return df * F * sqrt(T) * exp(-0.5 * d1 * d1) / sqrt(2 * np.pi)


def black_implied_vol(price: float, F: float, K: float, T: float, df: float, kind: str = "call") -> float:
    """Volatility that makes Black's price equal to `price` (Brent root search on 0.01%-500%)."""
    f = black_call if kind == "call" else black_put
    return float(brentq(lambda s: f(F, K, s, T, df) - price, 1e-4, 5.0))


# ---------- From quotes to a smooth smile ----------

def parity_forward(chain: pd.DataFrame, spot: float, n: int = 10) -> tuple[float, float]:
    """Forward F and discount factor df from put-call parity near the money.

    For European options c - p = df (F - K): regressing c - p on K gives slope -df and
    intercept df * F. Uses mid-quotes of the n strikes closest to spot that have two-sided call
    and put quotes, weighting each strike by 1 / (call spread + put spread).
    """
    two = chain[(chain["call_bid"] > 0) & (chain["call_ask"] > chain["call_bid"])
                & (chain["put_bid"] > 0) & (chain["put_ask"] > chain["put_bid"])]
    near = two.loc[(two["strike"] - spot).abs().sort_values().index[:n]]
    if len(near) < 3:
        raise ValueError("need at least three strikes near the money with two-sided call and put quotes")
    c = (near["call_bid"] + near["call_ask"]) / 2
    p = (near["put_bid"] + near["put_ask"]) / 2
    spread = (near["call_ask"] - near["call_bid"]) + (near["put_ask"] - near["put_bid"])
    slope, intercept = np.polyfit(near["strike"], c - p, 1, w=1 / np.sqrt(spread))
    df = -slope
    if not 0.5 < df <= 1.05:
        raise ValueError(f"put-call parity gives an implausible discount factor ({df:.3f})")
    return float(intercept / df), float(df)


def otm_quotes(chain: pd.DataFrame, F: float) -> pd.DataFrame:
    """Out-of-the-money puts (K < F) and calls (K >= F) with two-sided quotes.

    Out-of-the-money options are the more actively traded side at each strike. Returns columns
    strike, type ('put' or 'call'), bid, ask, mid.
    """
    rows = []
    for _, q in chain.iterrows():
        kind = "put" if q["strike"] < F else "call"
        bid, ask = q[f"{kind}_bid"], q[f"{kind}_ask"]
        if bid > 0 and ask > bid:
            rows.append({"strike": q["strike"], "type": kind, "bid": bid, "ask": ask, "mid": (bid + ask) / 2})
    return pd.DataFrame(rows)


def add_implied_vols(quotes: pd.DataFrame, F: float, T: float, df: float) -> pd.DataFrame:
    """Add each quote's Black implied vol (`iv`) and the vol width of half its bid-ask spread
    (`iv_err` = half-spread / vega). Quotes whose mid has no implied vol are dropped."""
    out = []
    for _, q in quotes.iterrows():
        try:
            iv = black_implied_vol(q["mid"], F, q["strike"], T, df, q["type"])
        except ValueError:
            continue
        vega = black_vega(F, q["strike"], iv, T, df)
        out.append({**q.to_dict(), "iv": iv, "iv_err": (q["ask"] - q["bid"]) / 2 / vega})
    return pd.DataFrame(out)


@dataclass
class Smile:
    """Smoothing spline of implied vol against log-moneyness ln(K/F), valid between k_lo and k_hi."""
    spline: UnivariateSpline
    F: float
    k_lo: float
    k_hi: float

    def vol(self, K):
        K = np.asarray(K, dtype=float)
        if np.any(K < self.k_lo - 1e-9) or np.any(K > self.k_hi + 1e-9):
            raise ValueError("strike outside the quoted range; this app does not extrapolate")
        return self.spline(np.log(K / self.F))


def fit_smile(iv_table: pd.DataFrame, F: float, smoothing: float = 0.01) -> Smile:
    """Weighted smoothing spline through the implied vols (as in Bliss and Panigirtzoglou 2002).

    Each vol is weighted by 1 / iv_err (the vol width of half its bid-ask spread), so tight
    quotes count more. The spline is as smooth as possible while the weighted squared misses
    add up to at most smoothing * n. The default, 0.01, keeps the misses far inside the spreads;
    larger values give a calmer curve that starts to miss quotes, and 0 passes through every
    quote. The spline is quartic (degree 4): the density depends on the curve's second
    derivative, and a cubic spline would leave kinks in the density at its knots.
    """
    if len(iv_table) < 8:
        raise ValueError(f"need at least 8 quotes with implied vols; got {len(iv_table)}")
    t = iv_table.sort_values("strike")
    x = np.log(t["strike"].to_numpy() / F)
    spline = UnivariateSpline(x, t["iv"].to_numpy(), w=1 / t["iv_err"].to_numpy(), k=4,
                              s=smoothing * len(t))
    return Smile(spline, F, float(t["strike"].min()), float(t["strike"].max()))


# ---------- Breeden-Litzenberger ----------

def bl_distribution(smile: Smile, T: float, df: float, step: float = 5.0) -> pd.DataFrame:
    """Call prices from the smooth smile on a grid, then Breeden-Litzenberger.

    Returns strike, call, cdf = P(S_T <= K) = 1 + (1/df) dc/dK, and pdf = (1/df) d2c/dK2
    (probability per index point), from the lowest to the highest quoted strike.
    """
    n = int(round((smile.k_hi - smile.k_lo) / step)) + 1
    K = np.linspace(smile.k_lo, smile.k_hi, n)
    h = K[1] - K[0]
    vols = smile.vol(K)
    if np.min(vols) <= 0:
        raise ValueError("the smoothed volatility curve drops below zero; it needs more smoothing")
    c = np.array([black_call(smile.F, k, v, T, df) for k, v in zip(K, vols)])
    cdf = 1 + np.gradient(c, h) / df
    pdf = np.empty_like(c)
    pdf[1:-1] = (c[2:] - 2 * c[1:-1] + c[:-2]) / h**2 / df
    pdf[0], pdf[-1] = pdf[1], pdf[-2]
    out = pd.DataFrame({"strike": K, "call": c, "cdf": cdf, "pdf": pdf})
    out.attrs["df"] = df
    return out


def df_of(dist: pd.DataFrame) -> float:
    return float(dist.attrs["df"])


def prob_below(dist: pd.DataFrame, x: float) -> float | None:
    """P(S_T <= x) from the distribution, or None if x is outside the quoted strikes."""
    K = dist["strike"].to_numpy()
    if x < K[0] or x > K[-1]:
        return None
    return float(np.interp(x, K, dist["cdf"].to_numpy()))


def density_checks(dist: pd.DataFrame) -> dict:
    """Sanity checks a valid distribution must pass.

    negative_mass: probability in regions where the density is below zero (should be ~0);
    cdf_outside: how far the cumulative probability goes below 0 or above 1 (should be 0);
    below, inside, above: probability below the lowest strike, between the strikes, above the
    highest strike (they add up to 1 by construction).
    """
    K, pdf, cdf = dist["strike"].to_numpy(), dist["pdf"].to_numpy(), dist["cdf"].to_numpy()
    step = np.diff(K).mean()
    out = {"negative_mass": float(-pdf[pdf < 0].sum() * step),
           "cdf_outside": float(max(0.0, -cdf.min(), cdf.max() - 1)), "below": float(cdf[0]),
           "inside": float(cdf[-1] - cdf[0]), "above": float(1 - cdf[-1])}
    out["valid"] = out["negative_mass"] < TOLERANCE and out["cdf_outside"] < TOLERANCE
    return out


TOLERANCE = 1e-3   # a distribution is valid if less than 0.1% of probability breaks a check
SMOOTHING_GRID = (0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0)


def auto_smile(iv_table: pd.DataFrame, F: float, T: float, df: float, grid=SMOOTHING_GRID):
    """The least smoothing on `grid` whose distribution passes density_checks.

    Malz (2014) picks his differencing step the same way: the smallest one that keeps the
    density non-negative. Returns (smoothing, smile, distribution, checks); raises ValueError
    if no level passes.
    """
    for s in grid:
        try:
            smile = fit_smile(iv_table, F, s)
            dist = bl_distribution(smile, T, df)
        except ValueError:
            continue
        checks = density_checks(dist)
        if checks["valid"]:
            return s, smile, dist, checks
    raise ValueError("no smoothing level gives a valid distribution for this expiration")


def smile_prices(smile: Smile, quotes: pd.DataFrame, T: float, df: float) -> np.ndarray:
    """Model price of each quoted option, using the smoothed vol at its strike."""
    vols = smile.vol(quotes["strike"].to_numpy())
    return np.array([black_put(smile.F, K, v, T, df) if t == "put" else black_call(smile.F, K, v, T, df)
                     for K, t, v in zip(quotes["strike"], quotes["type"], vols)])


def fit_report(model: np.ndarray, quotes: pd.DataFrame) -> dict:
    """Root-mean-square pricing error (index points) and the share of model prices inside the
    bid-ask spread. In-sample: these are the quotes the curve was fitted to."""
    model = np.asarray(model, dtype=float)
    inside = (model >= quotes["bid"].to_numpy()) & (model <= quotes["ask"].to_numpy())
    return {"rmse": float(np.sqrt(np.mean((model - quotes["mid"].to_numpy()) ** 2))),
            "inside_spread": float(inside.mean()), "n": int(len(quotes))}


def lognormal_cdf(F: float, s: float, x: float, T: float) -> float:
    """Black-Scholes (single lognormal) probability that S_T <= x, with mean F and volatility s."""
    if x <= 0:
        return 0.0
    return float(norm_cdf((log(x / F) + 0.5 * s * s * T) / (s * sqrt(T))))


def bucket_table(dist: pd.DataFrame, centers, h: float, F_ln: float | None = None,
                 s_ln: float | None = None, T: float | None = None) -> pd.DataFrame:
    """Probability that S_T lands in (K - h/2, K + h/2] for each center K inside the quoted range.

    `implied` is the probability of the bucket. `butterfly` is what a butterfly with strike
    spacing h measures on the smooth curve: (c(K-h) - 2c(K) + c(K+h)) / (df h), a
    triangle-weighted average over (K-h, K+h), so it differs a little from the bucket. Compare
    Project 1's butterflies with that column. Optionally adds Black-Scholes probabilities.
    """
    Kg, cg = dist["strike"].to_numpy(), dist["call"].to_numpy()
    rows = []
    for K in centers:
        lo, hi = prob_below(dist, K - h / 2), prob_below(dist, K + h / 2)
        if lo is None or hi is None or K - h < Kg[0] or K + h > Kg[-1]:
            continue
        c = np.interp([K - h, K, K + h], Kg, cg)
        row = {"strike": float(K), "implied": hi - lo,
               "butterfly": (c[0] - 2 * c[1] + c[2]) / (df_of(dist) * h)}
        if F_ln is not None:
            row["lognormal"] = lognormal_cdf(F_ln, s_ln, K + h / 2, T) - lognormal_cdf(F_ln, s_ln, K - h / 2, T)
        rows.append(row)
    return pd.DataFrame(rows)
