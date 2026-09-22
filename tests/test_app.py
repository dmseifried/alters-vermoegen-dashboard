"""Startet das Dashboard headless (streamlit AppTest) und prüft, dass kein
Tab eine Exception wirft — auch mit dem Schalter „nur belastbar"."""

import pytest
from streamlit.testing.v1 import AppTest

from src.load import PROJEKT, VERARBEITET


@pytest.fixture(scope="module")
def app():
    if not (VERARBEITET / "laender_jahr.parquet").exists():
        pytest.skip("Parquet-Dateien fehlen — erst `uv run python -m src.clean`")
    at = AppTest.from_file(str(PROJEKT / "app.py"), default_timeout=120)
    at.run()
    return at


def test_app_laeuft_ohne_fehler(app):
    assert not app.exception, [e.value for e in app.exception]
    assert len(app.tabs) == 4


def test_app_nur_belastbar(app):
    app.toggle[0].set_value(True).run()
    assert not app.exception, [e.value for e in app.exception]


def test_app_projektionsjahr(app):
    app.slider[0].set_value(2050).run()
    assert not app.exception, [e.value for e in app.exception]
