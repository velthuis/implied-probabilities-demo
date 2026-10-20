"""Smoke tests: the app runs on both saved files and shows the expected headline numbers."""
from streamlit.testing.v1 import AppTest


def test_app_runs_on_the_default_file():
    at = AppTest.from_file("../app.py", default_timeout=120).run()
    assert not at.exception
    assert at.metric[0].value == "100%"          # fit inside bid-ask
    assert at.metric[1].value == "8,080"         # forward from put-call parity, Oct 19, 2026 file
    assert not at.error


def test_app_runs_on_the_project_1_file():
    at = AppTest.from_file("../app.py", default_timeout=120).run()
    at.sidebar.radio[0].set_value("Saved Cboe download: SPX, Apr 27, 2022 (Project 1)").run()
    assert not at.exception
    assert at.metric[0].value == "100%"
    assert at.metric[1].value == "4,244"
    assert not at.error


def test_no_smoothing_hides_the_tail_table():
    at = AppTest.from_file("../app.py", default_timeout=120).run()
    at.sidebar.select_slider[0].set_value(0.0).run()
    assert not at.exception
    assert any("Not a valid distribution" in e.value for e in at.error)
