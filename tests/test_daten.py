"""Schlanke Tests zur Datenaufbereitung (Spezifikation Abschnitt 8)."""

import pandas as pd

from src.load import VAR_ANTEIL, WID_VARIABLEN, lade_wid_daten, lade_wpp_indikatoren

TOLERANZ = 0.005  # erlaubte Abweichung der Anteilssummen von 1


def test_namibia_wird_nicht_zu_nan():
    """Namibias ISO2-Code ist "NA" — pandas darf ihn nicht als fehlend lesen."""
    ind = lade_wpp_indikatoren()
    namibia = ind[ind["Location"] == "Namibia"]
    assert not namibia.empty
    assert set(namibia["ISO2_code"]) == {"NA"}


def test_namibia_in_laender_jahr(laender_jahr):
    assert "NA" in set(laender_jahr["iso2"])
    assert laender_jahr["iso2"].isna().sum() == 0


def test_keine_aggregate_in_laender_jahr(laender_jahr):
    """Nur Länder: jedes hat einen ISO3-Code, und kein Aggregat-Name taucht auf."""
    assert laender_jahr["iso3"].notna().all()
    assert laender_jahr["iso3"].str.len().eq(3).all()
    aggregate = {
        "World",
        "Africa",
        "Asia",
        "Europe",
        "Oceania",
        "Northern America",
        "Latin America and the Caribbean",
        "High-income countries",
    }
    assert aggregate.isdisjoint(set(laender_jahr["land"]))
    # Ein Land pro (iso2, jahr), rund 237 Länder
    assert not laender_jahr.duplicated(["iso2", "jahr"]).any()
    assert 230 <= laender_jahr["iso2"].nunique() <= 240


def test_anteilssummen_plausibel(laender_jahr, wid_dezile):
    """bottom50 + mittel50_90 + top10 ≈ 1 und Dezile summieren sich zu ≈ 1."""
    mit = laender_jahr.dropna(subset=["top10"])
    summe = mit["bottom50"] + mit["mittel50_90"] + mit["top10"]
    assert summe.between(1 - TOLERANZ, 1 + TOLERANZ).all()
    assert mit["top10"].between(0, 1).all()
    assert mit["top1"].le(mit["top10"]).all()

    dezsumme = wid_dezile.groupby(["iso2", "jahr"])["anteil"].sum()
    assert dezsumme.between(1 - TOLERANZ, 1 + TOLERANZ).all()


def test_nur_shwealj992(wid_lang):
    """Der Präfix `shweal` würde auch `shwealj999` fangen — das darf nicht passieren."""
    variablen = set(wid_lang["variable"])
    assert VAR_ANTEIL in variablen
    assert "shwealj999" not in variablen
    assert variablen <= set(WID_VARIABLEN)


def test_lade_wid_daten_filtert_exakt():
    """Direkt am Loader geprüft, unabhängig vom Cache: nur exakte Codes."""
    fr = lade_wid_daten(["FR"], ausgabe=False)
    assert set(fr["variable"]) <= set(WID_VARIABLEN)
    assert "shwealj999" not in set(fr["variable"])
    assert (fr["country"] == "FR").all()


def test_wertebereiche(laender_jahr):
    # Spezifikation nennt 10–60; der Heilige Stuhl (ab 2009) und Hongkong
    # (Projektion ab 2047) liegen real bei 62, daher Obergrenze 65.
    assert laender_jahr["medianalter"].between(10, 65).all()
    q = laender_jahr["quality_top10"].dropna()
    assert q.between(0, 5).all()
    assert pd.api.types.is_bool_dtype(laender_jahr["projektion"])
