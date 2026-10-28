"""The tests that came with cip.py. Both pass. Are they good tests?"""
import pytest

from cip import forward_rate


def test_equal_rates_give_the_spot_rate():
    assert forward_rate(0.99, 0.03, 0.03, 2.0) == pytest.approx(0.99)


def test_forward_rate():
    spot, r_usd, r_eur, T = 0.99, 0.046, 0.024, 2.0
    expected = spot * ((1 + r_usd) / (1 + r_eur)) ** T
    assert forward_rate(spot, r_usd, r_eur, T) == pytest.approx(expected)
