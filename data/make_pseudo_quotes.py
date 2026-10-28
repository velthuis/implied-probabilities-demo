"""Write a pseudo SPX quotes file in the layout of Cboe's delayed-quotes download.

The quotes are made up, not market data: prices come from Black's formula with an SVI volatility
smile (Gatheral 2004) whose shape resembles the SPX smile, then get a bid-ask spread and are
rounded to the tick, which adds the kind of noise real quotes have. The parameters below are the
"truth" behind the file, so tests can check the app against them.

Run from the repository root:  python data/make_pseudo_quotes.py
Units: index points, T in years, rates and volatilities as annual decimals.
"""
import csv
from datetime import date
from math import erf, exp, log, sqrt

import numpy as np

SPOT = 7600.00                   # index level
QUOTE_DATE = date(2026, 10, 19)
EXPIRATION = date(2027, 12, 17)
R = 0.045                        # risk-free rate, continuously compounded
Q = 0.012                        # dividend yield, continuously compounded
SVI = dict(a=-0.37, b=0.56, rho=0.45, m=0.63, s=0.78)   # total variance w(k) = sigma^2 T, k = ln(K/F)
SEED = 8615
OUT = "data/spx_pseudo_quotes_2026-10-19.csv"

# Strikes listed for a long-dated SPX series: wide steps in the wings, 50 points near the money.
STRIKES = ([float(k) for k in range(400, 2201, 200)] + [float(k) for k in range(2300, 3801, 100)]
           + [float(k) for k in range(3850, 9001, 50) if k not in (8850, 8950)]
           + [float(k) for k in range(9100, 9501, 100)] + [9550.0]
           + [float(k) for k in range(9600, 11401, 200)] + [12000.0])

T = (EXPIRATION - QUOTE_DATE).days / 365
DF = exp(-R * T)
F = SPOT * exp((R - Q) * T)


def norm_cdf(x: float) -> float:
    return 0.5 * (1 + erf(x / sqrt(2)))


def svi_vol(K: float) -> float:
    """Implied volatility at strike K from the SVI smile."""
    k = log(K / F)
    p = SVI
    w = p["a"] + p["b"] * (p["rho"] * (k - p["m"]) + sqrt((k - p["m"]) ** 2 + p["s"] ** 2))
    return sqrt(w / T)


def black(K: float, sigma: float) -> tuple[float, float, float]:
    """Black (1976) call and put prices and the call delta (in spot terms) at strike K."""
    sd = sigma * sqrt(T)
    d1 = (log(F / K) + 0.5 * sd * sd) / sd
    call = DF * (F * norm_cdf(d1) - K * norm_cdf(d1 - sd))
    return call, call - DF * (F - K), exp(-Q * T) * norm_cdf(d1)


def tick(x: float) -> float:
    """Cboe's SPX ticks: 0.05 below 3.00, 0.10 from 3.00 up."""
    t = 0.05 if x < 3 else 0.10
    return round(round(x / t) * t, 2)


def quote(price: float, otm: bool, rng) -> tuple[float, float]:
    """A bid and ask around `price`: spreads grow with the price, and in-the-money options (the less
    traded side) get wider ones. The mid is off the price by a little noise and the tick rounding."""
    spread = max(0.20, 0.125 * sqrt(price)) if otm else max(1.0, 0.004 * price + 0.1 * sqrt(price))
    mid = price + rng.normal(0, 0.03 * spread)
    bid = max(tick(mid - spread / 2), 0.05)
    ask = max(tick(mid + spread / 2), bid + 0.05)
    return bid, round(ask, 2)


def main():
    rng = np.random.default_rng(SEED)
    stamp = EXPIRATION.strftime("%y%m%d")
    rows = []
    for K in STRIKES:
        sigma = svi_vol(K)
        call, put, delta = black(K, sigma)
        cb, ca = quote(call, K >= F, rng)
        pb, pa = quote(put, K < F, rng)
        iv = f"{sigma:.4f}"
        sym = f"{K * 1000:08.0f}"
        rows.append([EXPIRATION.strftime("%a %b %d %Y"),
                     f"SPX{stamp}C{sym}", f"{(cb + ca) / 2:.2f}", 0, cb, ca, 0, iv, f"{delta:.4f}", 0,
                     int(rng.integers(0, 5000)), f"{K:.2f}",
                     f"SPX{stamp}P{sym}", f"{(pb + pa) / 2:.2f}", 0, pb, pa, 0, iv, f"{delta - exp(-Q * T):.4f}", 0,
                     int(rng.integers(0, 5000))])
    with open(OUT, "w", newline="") as f:
        f.write(f"S&P 500 INDEX (PSEUDO DATA: made-up quotes; see data/make_pseudo_quotes.py),Last: {SPOT:.2f},Change: 0\n")
        f.write(f'"Date: {QUOTE_DATE:%B} {QUOTE_DATE.day}, {QUOTE_DATE.year} at 11:40 PM EDT",Bid: 0,Ask: 0,Size: 0*0,Volume: 0\n')
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["Expiration Date", "Calls", "Last Sale", "Net", "Bid", "Ask", "Volume", "IV", "Delta",
                    "Gamma", "Open Interest", "Strike", "Puts", "Last Sale", "Net", "Bid", "Ask", "Volume",
                    "IV", "Delta", "Gamma", "Open Interest"])
        w.writerows(rows)
    print(f"wrote {OUT}: {len(rows)} strikes, F = {F:.2f}, df = {DF:.6f}, T = {T:.4f} years")


if __name__ == "__main__":
    main()
