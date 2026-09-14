"""Macht die Projektwurzel importierbar, damit `from src.load import …` in
den Tests funktioniert, egal von wo pytest gestartet wird."""

import sys
from pathlib import Path

import pandas as pd
import pytest

PROJEKT = Path(__file__).resolve().parents[1]
if str(PROJEKT) not in sys.path:
    sys.path.insert(0, str(PROJEKT))

from src.load import VERARBEITET


def _parquet(name: str) -> pd.DataFrame:
    """Liest eine aufbereitete Datei oder überspringt den Test, wenn
    `clean.py` noch nicht gelaufen ist."""
    datei = VERARBEITET / name
    if not datei.exists():
        pytest.skip(f"{datei.name} fehlt — erst `uv run python -m src.clean` ausführen")
    return pd.read_parquet(datei)


@pytest.fixture(scope="session")
def laender_jahr() -> pd.DataFrame:
    return _parquet("laender_jahr.parquet")


@pytest.fixture(scope="session")
def wid_dezile() -> pd.DataFrame:
    return _parquet("wid_dezile.parquet")


@pytest.fixture(scope="session")
def wid_lang() -> pd.DataFrame:
    return _parquet("wid_lang.parquet")
