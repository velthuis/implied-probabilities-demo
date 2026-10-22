"""Forward exchange rate from covered interest parity (CIP).

Units: spot and forward in USD per 1 EUR. r_usd and r_eur are risk-free zero rates as
decimals per year (0.046, not 4.6), continuously compounded. T is in years.
"""


def forward_rate(spot: float, r_usd: float, r_eur: float, T: float) -> float:
    """No-arbitrage forward rate, in USD per EUR, for delivery in T years."""
    growth = (1 + r_usd) / (1 + r_eur)  # USD interest relative to EUR interest
    return spot * growth ** T
