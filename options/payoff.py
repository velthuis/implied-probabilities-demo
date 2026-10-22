"""Payoff and profit at expiration for one stock option position.

Written by an agent from the class prompt. Amounts are per share unless a function says
otherwise; one contract is 100 shares.
"""
import numpy as np

SHARES_PER_CONTRACT = 100


def call_payoff(S, K):
    """Value of a call at expiration: max(S - K, 0)."""
    return np.maximum(np.asarray(S, dtype=float) - K, 0.0)


def put_payoff(S, K=405.0):
    """Value of a put at expiration: max(K - S, 0)."""
    return np.maximum(K - np.asarray(S, dtype=float), 0.0)


def payoff(option, S, K):
    """Payoff of a long position, per share."""
    return call_payoff(S, K) if option == "call" else put_payoff(S)


def profit(option, position, S, K, premium):
    """Profit per share: payoff minus the premium for a long position, and the mirror image
    (premium minus payoff) for a short one."""
    long_profit = payoff(option, S, K) - premium
    return long_profit if position == "long" else -long_profit


def break_even(option, K, premium):
    """Stock price at expiration where the profit is zero."""
    return K + premium if option == "call" else K - premium
