"""
Qualitäts- und Abdeckungsanalyse der WID-Vermögensdaten.

Beantwortet für alle WID-Länder:
- Wie viele haben überhaupt eine Reihe zu `shwealj992`?
- Wie viele haben je Qualität >= 3 („belastbar") erreicht — und bis zu
  welchem Jahr?
- Wie verteilt sich das über die Weltregionen?

Schreibt `data/processed/wid_qualitaet.parquet` (dieselbe Datei, die auch
`clean.py` erzeugt — die Berechnung liegt in `clean.wid_qualitaet`) und gibt
die Zusammenfassung für Präsentation und Phase-1-Bericht auf der Konsole aus.

Aufruf:  uv run python -m src.abdeckung
"""

import pandas as pd

from src.clean import (
    JAHR_BIS,
    JAHR_VON,
    kosovo_vereinheitlichen,
    wid_qualitaet,
    wpp_regionen_iso2,
)
from src.load import (
    BELASTBAR,
    VAR_ANTEIL,
    VERARBEITET,
    lade_wid_daten,
    lade_wid_laender,
    lade_wid_metadaten,
    lade_wpp_indikatoren,
)


def lade_wid_cache(codes: list[str]) -> pd.DataFrame:
    """Nutzt den Parquet-Cache aus clean.py, wenn vorhanden; sonst Rohdaten."""
    cache = VERARBEITET / "wid_lang.parquet"
    if cache.exists():
        print(f"WID: Cache {cache.name} gelesen")
        return pd.read_parquet(cache)
    wid = lade_wid_daten(codes)
    VERARBEITET.mkdir(parents=True, exist_ok=True)
    wid.to_parquet(cache, index=False)
    return wid


def bericht(q: pd.DataFrame) -> None:
    """Druckt die Kennzahlen, die in Spezifikation 6.1 Schritt 2 verlangt sind."""
    pd.set_option("display.width", 160)
    mit = q[q["hat_daten"]]
    bel = mit[mit["n_jahre_belastbar"] > 0]

    print("\n" + "=" * 70)
    print(f"QUALITÄT DER VERMÖGENSDATEN ({VAR_ANTEIL}, {JAHR_VON}–{JAHR_BIS})")
    print("=" * 70)
    print(f"Länder in WID_countries (2-Zeichen-Codes):   {len(q)}")
    print(f"davon mit Vermögensreihe:                    {len(mit)}")
    print(f"davon je Qualität >= {BELASTBAR} erreicht:            {len(bel)}")
    print(
        f"davon nur mit Imputationspapier als Quelle:  {int(mit['nur_imputation'].sum())}"
    )

    print("\nHöchste je erreichte Qualitätsstufe (Anzahl Länder):")
    print(mit["max_quality"].value_counts(dropna=False).sort_index().to_string())

    print("\nNach Weltregion:")
    tab = q.groupby("region").agg(
        laender=("iso2", "count"),
        mit_daten=("hat_daten", "sum"),
        belastbar=("n_jahre_belastbar", lambda n: int((n > 0).sum())),
    )
    tab["anteil_belastbar"] = (tab["belastbar"] / tab["mit_daten"]).map("{:.0%}".format)
    print(tab.to_string())

    print(f"\nLänder mit Qualität >= {BELASTBAR} — bis zu welchem Jahr?")
    spalten = [
        "iso2",
        "land_wid",
        "region",
        "max_quality",
        "avg_quality",
        "erstes_belastbares_jahr",
        "letztes_belastbares_jahr",
        "n_jahre_belastbar",
        "anteil_quality_0",
    ]
    tabelle = bel[spalten].sort_values(
        ["letztes_belastbares_jahr", "n_jahre_belastbar"], ascending=False
    )
    with pd.option_context("display.float_format", "{:.2f}".format):
        print(tabelle.to_string(index=False))

    print("\nLetztes belastbares Jahr (Verteilung):")
    print(
        bel["letztes_belastbares_jahr"]
        .value_counts()
        .sort_index(ascending=False)
        .to_string()
    )

    print("\nAnteil der Jahre mit Qualität 0 über alle Länder mit Daten:")
    print(mit["anteil_quality_0"].describe()[["mean", "25%", "50%", "75%"]].to_string())


def main() -> None:
    laender = lade_wid_laender()
    print(f"{len(laender)} echte Länder in WID_countries.csv")

    wid = lade_wid_cache(laender["alpha2"].tolist())
    n = len(wid)
    wid = wid[wid["year"].between(JAHR_VON, JAHR_BIS)]
    print(f"Filter Jahre {JAHR_VON}–{JAHR_BIS}: {n:,} -> {len(wid):,} Zeilen")

    meta = lade_wid_metadaten(laender["alpha2"].tolist())
    wid, meta, laender = kosovo_vereinheitlichen(wid, meta, laender)
    # Region aus der WPP-Hierarchie, damit C9 dieselbe Einteilung nutzt wie C8
    regionen = wpp_regionen_iso2(lade_wpp_indikatoren())
    q = wid_qualitaet(wid, meta, laender, regionen)

    VERARBEITET.mkdir(parents=True, exist_ok=True)
    q.to_parquet(VERARBEITET / "wid_qualitaet.parquet", index=False)
    bericht(q)
    print(f"\ngespeichert: {VERARBEITET / 'wid_qualitaet.parquet'}")


if __name__ == "__main__":
    main()
