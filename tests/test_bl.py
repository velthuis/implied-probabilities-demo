"""Checks for Breeden-Litzenberger on a smoothed smile.

Each test compares the code with something computed a different way: a textbook number, the
raw file itself, scipy's lognormal distribution, a hand calculation, or the quotes. The last
tests are guards that document known behavior.
"""
import io
from datetime import date
from math import exp, sqrt

import numpy as np
import pandas as pd
import pytest
from scipy.stats import lognorm

from bl import (add_implied_vols, ask_market, auto_smile, equity_premium, real_world, black_call, black_implied_vol, black_put, bl_distribution,
                default_series, density_checks, fit_report, fit_smile, one_series,
                otm_quotes, parity_forward, prob_below, read_cboe_csv, series_list, smile_prices)
from pricing import bs_call, bs_put

NEW = "data/spx_quotedata_2026-10-19.csv"      # the app's saved Cboe download


def snapshot(path=NEW):
    chain, spot, quote_date = read_cboe_csv(path)
    expiration, root = series_list(chain)[0]
    T = (expiration - quote_date).days / 365
    one = one_series(chain, expiration, root)
    F, df = parity_forward(one, spot)
    return one, spot, T, F, df


def quotes_from(call_price, strikes, F, df, half_spread):
    """A chain whose mid-quotes are exact prices from `call_price` (puts by parity)."""
    rows = []
    for K in strikes:
        c = call_price(K)
        p = c - df * (F - K)
        rows.append({"strike": K, "call_bid": c - half_spread, "call_ask": c + half_spread,
                     "put_bid": p - half_spread, "put_ask": p + half_spread})
    return pd.DataFrame(rows)


# ---------- Reading the raw Cboe file ----------

def test_reads_the_new_cboe_file():
    # Values typed from the Oct 19, 2026 download: header and the 7,000 row.
    chain, spot, quote_date = read_cboe_csv(NEW)
    assert spot == 7690.73
    assert quote_date == date(2026, 10, 19)
    assert series_list(chain) == [(date(2027, 12, 17), "SPX")]
    assert len(chain) == 145
    row = chain[chain["strike"] == 7000].iloc[0]
    assert (row["call_bid"], row["call_ask"], row["put_bid"], row["put_ask"]) == (1274.0, 1278.9, 256.5, 258.4)


def test_reader_separates_expirations_and_roots():
    text = (
        "Standard & Poors 500 Index,Last: 5,000.50,Change: 1\n"
        '"Date: October 16, 2026 at 4:15 PM EDT",Bid: 1,Ask: 2\n'
        "Expiration Date,Calls,Last Sale,Net,Bid,Ask,Volume,IV,Delta,Gamma,Open Interest,Strike,"
        "Puts,Last Sale,Net,Bid,Ask,Volume,IV,Delta,Gamma,Open Interest\n"
        "Fri Nov 20 2026,SPX261120C05000000,0,0,10,11,0,0,0,0,5,5000,SPX261120P05000000,0,0,8,9,0,0,0,0,6\n"
        "Fri Nov 20 2026,SPXW261120C05000000,0,0,12,13,0,0,0,0,5,5000,SPXW261120P05000000,0,0,7,8,0,0,0,0,6\n"
        "Fri Dec 18 2026,SPX261218C05000000,0,0,20,21,0,0,0,0,5,5000,SPX261218P05000000,0,0,15,16,0,0,0,0,6\n"
    )
    chain, spot, quote_date = read_cboe_csv(io.StringIO(text))
    assert spot == 5000.50 and quote_date == date(2026, 10, 16)
    assert series_list(chain) == [(date(2026, 11, 20), "SPX"), (date(2026, 11, 20), "SPXW"),
                                  (date(2026, 12, 18), "SPX")]
    assert one_series(chain, date(2026, 11, 20), "SPXW")["call_bid"].tolist() == [12.0]


# ---------- Building blocks ----------

def test_black_matches_hull_example():
    # Hull, Ch. 15: S0 = 42, K = 40, r = 10%, sigma = 20%, T = 0.5 -> c = 4.76, p = 0.81.
    S, K, r, s, T = 42.0, 40.0, 0.10, 0.20, 0.5
    F, df = S * exp(r * T), exp(-r * T)
    assert black_call(F, K, s, T, df) == pytest.approx(4.76, abs=0.005)
    assert black_put(F, K, s, T, df) == pytest.approx(0.81, abs=0.005)


def test_implied_vol_inverts_the_hull_price():
    # Hull's call costs 4.76 at 20% volatility, so 4.7594 must give back 20%.
    F, df = 42 * exp(0.05), exp(-0.05)
    assert black_implied_vol(4.7594, F, 40.0, 0.5, df, "call") == pytest.approx(0.20, abs=1e-4)


def test_iv_width_is_half_spread_over_vega():
    # One call quoted 4.66 / 4.86 around Hull's 4.76: its vol must be 20%, and the vol width of
    # half the spread must be 0.10 / vega, with vega from a finite difference (not our formula).
    F, df, T, K = 42 * exp(0.05), exp(-0.05), 0.5, 40.0
    mid = black_call(F, K, 0.20, T, df)
    q = pd.DataFrame({"strike": [K], "type": ["call"], "bid": [mid - 0.10], "ask": [mid + 0.10], "mid": [mid]})
    out = add_implied_vols(q, F, T, df).iloc[0]
    vega_fd = (black_call(F, K, 0.2001, T, df) - black_call(F, K, 0.1999, T, df)) / 0.0002
    assert out["iv"] == pytest.approx(0.20, abs=1e-6)
    assert out["iv_err"] == pytest.approx(0.10 / vega_fd, rel=1e-4)


def test_parity_recovers_forward_and_discount_factor():
    # Black-Scholes prices with S0 = 100, r = 4%: parity must give F = 100 e^0.04 and df = e^-0.04.
    # Calls get wide spreads and puts narrow ones, so only mid-quotes give the right answer.
    S, r, sigma, T = 100.0, 0.04, 0.25, 1.0
    strikes = np.arange(80.0, 121.0, 5.0)
    calls = np.array([bs_call(S, k, r, sigma, T) for k in strikes])
    puts = np.array([bs_put(S, k, r, sigma, T) for k in strikes])
    chain = pd.DataFrame({"strike": strikes, "call_bid": calls - 0.5, "call_ask": calls + 0.5,
                          "put_bid": puts - 0.05, "put_ask": puts + 0.05})
    F, df = parity_forward(chain, S)
    assert df == pytest.approx(exp(-r * T), abs=1e-9)
    assert F == pytest.approx(S * exp(r * T), abs=1e-6)


def test_quotes_without_a_bid_are_left_out():
    chain = pd.DataFrame({"strike": [90.0, 95.0, 105.0], "call_bid": [12.0, 8.0, 0.0],
                          "call_ask": [13.0, 9.0, 0.4], "put_bid": [0.0, 1.0, 6.0], "put_ask": [0.5, 1.4, 7.0]})
    q = otm_quotes(chain, 100.0)
    assert q["strike"].tolist() == [95.0]          # the 90 put and the 105 call have no bid


def test_fit_report_hand_worked():
    # Errors of +1, -1, +3, -3 points against a half-spread of 2: two of four inside, RMS sqrt(5).
    q = pd.DataFrame({"mid": [10.0, 20.0, 30.0, 40.0]})
    q["bid"], q["ask"] = q["mid"] - 2, q["mid"] + 2
    rep = fit_report(q["mid"].to_numpy() + np.array([1.0, -1.0, 3.0, -3.0]), q)
    assert rep["inside_spread"] == pytest.approx(0.5)
    assert rep["rmse"] == pytest.approx(sqrt(5.0))


# ---------- Breeden-Litzenberger recovers known distributions ----------

def test_flat_smile_gives_the_lognormal():
    # Black-Scholes prices at one volatility: the distribution must be scipy's lognormal.
    F, T, df, s = 4300.0, 1.0, 0.97, 0.20
    chain = quotes_from(lambda K: black_call(F, K, s, T, df), np.arange(2000.0, 7001.0, 50.0), F, df, 0.2)
    dist = bl_distribution(fit_smile(add_implied_vols(otm_quotes(chain, F), F, T, df), F), T, df)
    truth = lognorm(s=s * sqrt(T), scale=F * exp(-0.5 * s * s * T))
    for x in np.arange(2600.0, 6401.0, 200.0):
        assert prob_below(dist, x) == pytest.approx(truth.cdf(x), abs=1e-4)
    inner = dist.iloc[5:-5]
    assert np.allclose(inner["pdf"], truth.pdf(inner["strike"]), atol=1e-7)


def test_recovers_a_two_peaked_distribution():
    # Prices from a mix of two lognormals (a shape no single lognormal has). The cumulative
    # probabilities must match scipy's, computed without our code.
    T, df = 0.75, exp(-0.03 * 0.75)
    comps = [(0.3, 3300.0, 0.30), (0.7, 4400.0, 0.15)]
    F = sum(w * m for w, m, _ in comps)
    price = lambda K: sum(w * black_call(m, K, s, T, df) for w, m, s in comps)
    chain = quotes_from(price, np.arange(1500.0, 7501.0, 50.0), F, df, 0.25)
    dist = bl_distribution(fit_smile(add_implied_vols(otm_quotes(chain, F), F, T, df), F), T, df)
    truth = lambda x: sum(w * lognorm(s=s * sqrt(T), scale=m * exp(-0.5 * s * s * T)).cdf(x)
                          for w, m, s in comps)
    for x in np.arange(2000.0, 6501.0, 250.0):
        assert prob_below(dist, x) == pytest.approx(truth(x), abs=0.005)


# ---------- The snapshot ----------

def test_tails_agree_with_option_spreads_on_the_snapshot():
    # Model-free check: a tight put spread pays about (K2 - K1) when the index ends below K1, so
    # P(S_T < (K1 + K2)/2) ~ (p(K2) - p(K1)) / ((K2 - K1) df); call spreads give the right tail.
    one, spot, T, F, df = snapshot()
    dist = bl_distribution(fit_smile(add_implied_vols(otm_quotes(one, F), F, T, df), F), T, df)
    put_mid = (one["put_bid"] + one["put_ask"]) / 2
    call_mid = (one["call_bid"] + one["call_ask"]) / 2
    k = one["strike"].to_numpy()
    for move in (0.10, 0.20, 0.30, 0.40):
        i = int(np.searchsorted(k, (1 - move) * spot))
        below = (put_mid[i] - put_mid[i - 1]) / ((k[i] - k[i - 1]) * df)
        assert prob_below(dist, (k[i] + k[i - 1]) / 2) == pytest.approx(below, abs=0.01)
        j = int(np.searchsorted(k, (1 + move) * spot))
        above = (call_mid[j - 1] - call_mid[j]) / ((k[j] - k[j - 1]) * df)
        assert 1 - prob_below(dist, (k[j] + k[j - 1]) / 2) == pytest.approx(above, abs=0.01)


def test_implied_vols_match_cboes_own():
    # Cboe's file has its own implied-vol column, computed with Cboe's model and inputs. Ours,
    # from the mid-quotes and the parity forward, must agree within one vol point.
    one, spot, T, F, df = snapshot()
    q = add_implied_vols(otm_quotes(one, F), F, T, df)
    cboe = one.set_index("strike")
    theirs = np.array([cboe.loc[K, f"{t}_iv_cboe"] for K, t in zip(q["strike"], q["type"])])
    assert (theirs > 0).all()
    assert np.abs(q["iv"].to_numpy() - theirs).max() < 0.01


def test_snapshot_distribution_is_valid():
    # No negative probabilities, cumulative probabilities between 0 and 1, and a good fit.
    one, spot, T, F, df = snapshot()
    quotes = add_implied_vols(otm_quotes(one, F), F, T, df)
    smile = fit_smile(quotes, F)
    dist = bl_distribution(smile, T, df)
    chk = density_checks(dist)
    assert chk["valid"] and chk["negative_mass"] < 1e-4 and chk["cdf_outside"] == 0.0
    assert 0 < chk["below"] < 0.02 and 0 < chk["above"] < 0.02
    # Two closed-form results checked against each other: the density, integrated numerically,
    # must give the probability that the cumulative probabilities say lies between the strikes.
    trapezoid = getattr(np, "trapezoid", None) or np.trapz
    assert trapezoid(dist["pdf"], dist["strike"]) == pytest.approx(chk["inside"], abs=1e-3)
    assert fit_report(smile_prices(smile, quotes, T, df), quotes)["inside_spread"] >= 0.9


def test_ask_the_market_on_a_flat_smile():
    # With one volatility, "Ask the market" must give scipy's lognormal for both sides, and the two
    # sides must add up to 1. Beyond the quoted strikes it reports a bound, not a number.
    F, T, df, s = 4300.0, 1.0, 0.97, 0.20
    chain = quotes_from(lambda K: black_call(F, K, s, T, df), np.arange(2000.0, 7001.0, 50.0), F, df, 0.2)
    dist = bl_distribution(fit_smile(add_implied_vols(otm_quotes(chain, F), F, T, df), F), T, df)
    truth = lognorm(s=s * sqrt(T), scale=F * exp(-0.5 * s * s * T))
    lo, hi = ask_market(dist, 3500.0, "below", F, s, T), ask_market(dist, 3500.0, "above", F, s, T)
    assert lo["implied"] == pytest.approx(truth.cdf(3500.0), abs=1e-4)
    assert lo["bs"] == pytest.approx(truth.cdf(3500.0), abs=1e-9)
    assert lo["implied"] + hi["implied"] == pytest.approx(1.0)
    assert lo["bound"] is None and hi["bound"] is None
    low = dist["strike"].iloc[0]                                 # the lowest strike with a usable quote
    far = ask_market(dist, 1000.0, "below", F, s, T)
    assert far["bound"] == "at most" and far["implied"] == pytest.approx(truth.cdf(low), abs=1e-4)
    assert ask_market(dist, 1000.0, "above", F, s, T)["bound"] == "at least"


def test_real_world_reweighting_of_a_lognormal():
    # Power utility turns a lognormal risk-neutral density into another lognormal whose log-mean is
    # higher by gamma * s^2 * T, so the expected return above the risk-free rate is gamma * s^2 a
    # year. Both follow from the formula on paper; scipy gives the shifted distribution.
    F, T, s, gamma = 4300.0, 1.0, 0.20, 2.0
    K = np.arange(500.0, 20001.0, 5.0)
    q_dist = lognorm(s=s * sqrt(T), scale=F * exp(-0.5 * s * s * T))
    q = pd.DataFrame({"strike": K, "pdf": q_dist.pdf(K)})
    p = real_world(q, gamma)
    p_truth = lognorm(s=s * sqrt(T), scale=F * exp(-0.5 * s * s * T + gamma * s * s * T))
    for x in (3000.0, 4300.0, 6000.0):
        assert np.interp(x, p["strike"], p["cdf"]) == pytest.approx(p_truth.cdf(x), abs=1e-4)
    assert equity_premium(q, p, T) == pytest.approx(gamma * s * s, abs=1e-4)
    # No fear, no difference; more fear, a smaller real-world chance of a big fall.
    p0 = real_world(q, 0.0)
    assert np.interp(3500.0, p0["strike"], p0["cdf"]) == pytest.approx(q_dist.cdf(3500.0), abs=1e-4)
    falls = [np.interp(0.8 * F, real_world(q, g)["strike"], real_world(q, g)["cdf"]) for g in (0.0, 1.0, 3.0)]
    assert falls[0] > falls[1] > falls[2]


def test_density_checks_catch_bad_distributions():
    K = np.arange(100.0, 106.0)
    bad = pd.DataFrame({"strike": K, "call": 0.0, "cdf": [0.1, 0.4, 0.8, 1.02, 1.03, 1.03],
                        "pdf": [0.3, 0.3, -0.02, 0.0, 0.0, 0.0]})
    chk = density_checks(bad)
    assert chk["cdf_outside"] == pytest.approx(0.03)
    assert chk["negative_mass"] == pytest.approx(0.02)
    assert not chk["valid"]


def test_automatic_smoothing_picks_the_least_that_passes():
    one, spot, T, F, df = snapshot()
    quotes = add_implied_vols(otm_quotes(one, F), F, T, df)
    s, smile, dist, chk = auto_smile(quotes, F, T, df)
    assert s == 0.01 and chk["valid"]
    s2, *_ = auto_smile(quotes, F, T, df, grid=(0.0, 0.0003, 0.01))   # 0 and 0.0003 fail
    assert s2 == 0.01


def test_default_expiration_is_nearest_one_year_with_enough_strikes():
    rows = []
    for exp_, n in ((date(2026, 11, 20), 30), (date(2027, 10, 15), 30), (date(2027, 12, 17), 5)):
        for K in np.arange(1000.0, 1000.0 + 50 * n, 50.0):
            rows.append({"expiration": exp_, "root": "SPX", "strike": K, "call_bid": 1.0, "call_ask": 1.5,
                         "put_bid": 1.0, "put_ask": 1.5})
    chain = pd.DataFrame(rows)
    assert default_series(chain, date(2026, 10, 19)) == (date(2027, 10, 15), "SPX")


# ---------- Guards: they document known behavior, not an independent number ----------

def test_no_smoothing_gives_negative_probabilities():
    # A curve through every quote inherits their noise: the density goes negative somewhere,
    # which is why we smooth.
    one, spot, T, F, df = snapshot()
    quotes = add_implied_vols(otm_quotes(one, F), F, T, df)
    assert density_checks(bl_distribution(fit_smile(quotes, F, smoothing=0.0), T, df))["negative_mass"] > 0.01


def test_too_much_smoothing_breaks_the_fit():
    # A nearly straight curve misses most quotes, and its prices imply a negative probability of
    # ending below the lowest strike (an arbitrage), which density_checks reports.
    one, spot, T, F, df = snapshot()
    quotes = add_implied_vols(otm_quotes(one, F), F, T, df)
    smile = fit_smile(quotes, F, smoothing=10.0)
    assert fit_report(smile_prices(smile, quotes, T, df), quotes)["inside_spread"] < 0.5
    assert not density_checks(bl_distribution(smile, T, df))["valid"]


def test_rejects_bad_inputs():
    with pytest.raises(ValueError):
        black_call(100.0, 100.0, -0.2, 1.0, 1.0)
    with pytest.raises(ValueError, match="not a Cboe quotes file"):
        read_cboe_csv(io.StringIO("strike,bid,ask\n100,1,2\n"))
    with open(NEW) as f:
        broken = f.read().replace(",7000.00,", ",7,000.00,")      # an unquoted thousands separator
    with pytest.raises(ValueError, match="columns"):
        read_cboe_csv(io.StringIO(broken))
    one, spot, T, F, df = snapshot()
    quotes = add_implied_vols(otm_quotes(one, F), F, T, df)
    with pytest.raises(ValueError, match="at least 8"):
        fit_smile(quotes.head(5), F)
    with pytest.raises(ValueError, match="does not extrapolate"):
        fit_smile(quotes, F).vol(100.0)
    assert prob_below(bl_distribution(fit_smile(quotes, F), T, df), 50.0) is None
