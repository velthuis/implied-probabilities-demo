"""Smoke tests: the app runs on the saved file and shows the expected headline numbers."""
from streamlit.testing.v1 import AppTest


def test_app_runs_on_the_default_file():
    at = AppTest.from_file("../app.py", default_timeout=120).run()
    assert not at.exception
    assert at.metric[0].value == "100%"          # fit inside bid-ask
    assert at.metric[1].value == "7,897"         # forward from put-call parity (the generator used 7,897.00)
    assert not at.error


def test_ask_the_market():
    # The default question (a fall of 20% or more) matches the tail table; a rise of 20% too; a level
    # below the lowest strike gives a bound.
    at = AppTest.from_file("../app.py", default_timeout=120).run()
    assert at.metric[2].value == "10.5%"          # options market, fall of 20% or more
    assert at.metric[3].value == "8.8%"           # Black-Scholes
    at.radio(key="ask_side").set_value("above").run()
    assert at.metric[2].value == "18.3%"
    at.radio(key="ask_unit").set_value("an index level").run()
    at.number_input(key="ask_level_above").set_value(20000.0).run()
    assert at.metric[2].value.startswith("at most")
    assert not at.exception


def test_fear_slider():
    # At the default fear level (2) the real-world chance of a 20% fall is well below the market's
    # 10.5%, and the prices imply an equity premium. At 0 the real world equals the market over the
    # quoted strikes; it leaves out the 0.09% below the lowest strike, so it shows 10.4%.
    at = AppTest.from_file("../app.py", default_timeout=120).run()
    value = lambda label: next(m.value for m in at.metric if m.label.startswith(label))
    assert value("Fall of 20% or more, real world") == "3.8%"
    assert value("Expected return above the risk-free rate") == "5.3% a year"
    at.slider(key="gamma").set_value(0.0).run()
    assert value("Fall of 20% or more, real world") == "10.4%"
    assert value("Expected return above the risk-free rate") == "0.0% a year"
    assert not at.exception


def test_no_smoothing_hides_the_tail_table():
    at = AppTest.from_file("../app.py", default_timeout=120).run()
    at.sidebar.select_slider[0].set_value(0.0).run()
    assert not at.exception
    assert any("Not a valid distribution" in e.value for e in at.error)
