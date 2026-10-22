"""Tests the agent wrote for payoff.py. Run with:  pytest options"""
import pytest

from payoff import break_even, payoff, profit


def test_call_example_from_class():
    # K = 405, price 17.65: at 425 the payoff is 20 and the profit 2.35 per share
    assert payoff("call", 425, 405) == pytest.approx(20.0)
    assert profit("call", "long", 425, 405, 17.65) == pytest.approx(2.35)


def test_put_example_from_class():
    # K = 405, price 20: at 380 the payoff is 25 and the profit 5 per share
    assert payoff("put", 380, 405) == pytest.approx(25.0)
    assert profit("put", "long", 380, 405, 20.0) == pytest.approx(5.0)


def test_short_is_the_mirror_image():
    assert profit("call", "short", 425, 405, 17.65) == pytest.approx(-2.35)
    assert profit("put", "short", 380, 405, 20.0) == pytest.approx(-5.0)


def test_break_even():
    assert break_even("call", 405, 17.65) == pytest.approx(422.65)
    assert break_even("put", 405, 20.0) == pytest.approx(385.0)
