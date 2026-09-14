"""
Rohdaten einlesen.

Hier steht alles, was direkt aus `data/raw/` liest. Keine Aufbereitung,
nur Einlesen mit den richtigen Parametern (Trennzeichen, NA-Behandlung,
Spaltenauswahl). Die Aufbereitung passiert in `clean.py`.

Konstanten, die im ganzen Projekt gelten (Pfade, Variablencodes,
Qualitätsschwelle), sind ebenfalls hier definiert.
"""

from pathlib import Path

import pandas as pd

# --- Pfade -----------------------------------------------------------------
# Relativ zur Projektwurzel, damit die Skripte von überall laufen.
PROJEKT = Path(__file__).resolve().parents[1]
ROH_WPP = PROJEKT / "data" / "raw" / "wpp"
ROH_WID = PROJEKT / "data" / "raw" / "wid"
VERARBEITET = PROJEKT / "data" / "processed"

# --- Definitionen aus der Spezifikation (Abschnitt 4) -----------------------
# „Belastbar" heißt: WID-Qualitätsscore mindestens 3 (Skala 0–5).
BELASTBAR = 3

# Vertiefungsländer (festgelegt nach Phase 1, Spezifikation Abschnitt 4).
# Spannweite Niger–Japan deckt die Demografie ab, Japan–USA die Datenqualität.
VERTIEFUNGSLAENDER = {
    "FR": "Frankreich",
    "US": "USA",
    "DE": "Deutschland",
    "IN": "Indien",
    "CN": "China",
    "JP": "Japan",
    "NE": "Niger",
    "ZA": "Südafrika",
}

# Quellenangaben für Chart-Fußzeilen.
QUELLE_WPP = "UN World Population Prospects 2024, Medium-Variante"
QUELLE_WID = "World Inequality Database (wid.world), Abruf 9.9.2026"

# WID-Variablencodes. Aufbau: Typ + Konzept + Bevölkerungseinheit + Alter.
# s = share, a = average, t = threshold, hweal = Netto-Privatvermögen,
# j = equal-split adults, 992 = Erwachsene ab 20.
# Achtung: `shwealj999` (alle Altersgruppen) ist eine andere Reihe und wird
# bewusst NICHT geladen — daher exakte Codes statt Präfixfilter.
VAR_ANTEIL = "shwealj992"  # Vermögensanteil einer Gruppe (Bruch von 1)
VAR_MITTEL = "ahwealj992"  # Durchschnittsvermögen (lokale Währung)
VAR_SCHWELLE = "thwealj992"  # Schwellenwert (lokale Währung)
VAR_PPP = "xlcuspi999"  # Kaufkraftparität lokale Währung je US-Dollar
VAR_PREISINDEX = "inyixxi999"  # Preisindex Nationaleinkommen, = 1 im Basisjahr
WID_VARIABLEN = [VAR_ANTEIL, VAR_MITTEL, VAR_SCHWELLE, VAR_PPP, VAR_PREISINDEX]

# Perzentilgruppen. Dezile für Lorenzkurven, Gruppen für die Kennzahlen.
GRUPPEN = ["p0p50", "p50p90", "p90p100", "p99p100"]
DEZILE = [f"p{i}p{i + 10}" for i in range(0, 100, 10)]
# p0p100: Durchschnitt über alle. p50p100 und p50p51: Schwelle = Median
# (beide Codes liefern in WID denselben Wert, wird in clean.py geprüft).
PERZENTILE = sorted(set(GRUPPEN + DEZILE + ["p0p100", "p50p100", "p50p51"]))

# --- WPP -------------------------------------------------------------------
WPP_INDIKATOR_SPALTEN = [
    "LocID",
    "ISO2_code",
    "ISO3_code",
    "Location",
    "LocTypeName",
    "ParentID",
    "Time",
    "TPopulation1July",
    "MedianAgePop",
    "TFR",
    "LEx",
    "LE65",
]

WPP_ALTER_SPALTEN = [
    "LocID",
    "ISO2_code",
    "ISO3_code",
    "Location",
    "LocTypeName",
    "Time",
    "AgeGrp",
    "AgeGrpStart",
    "PopMale",
    "PopFemale",
    "PopTotal",
]


def _lese_wpp(datei: Path, spalten: list[str]) -> pd.DataFrame:
    """Liest eine WPP-CSV mit den projektweit nötigen Einstellungen.

    - `encoding="utf-8-sig"`: die Dateien beginnen mit einem BOM, sonst
      hieße die erste Spalte "\\ufeffSortOrder".
    - `keep_default_na=False` + `na_values=[""]`: nur leere Felder sind NA.
      Sonst würde Namibias ISO2-Code "NA" zu einem fehlenden Wert.
    """
    return pd.read_csv(
        datei,
        usecols=spalten,
        encoding="utf-8-sig",
        keep_default_na=False,
        na_values=[""],
        low_memory=False,
    )


def lade_wpp_indikatoren() -> pd.DataFrame:
    """Kennzahlen pro Ort und Jahr (1950–2101, Medium-Variante), ungefiltert.

    Enthält auch Aggregate (Welt, Regionen) — die Filterung auf Länder
    passiert in clean.py, weil die Aggregate dort für die Regionszuordnung
    noch gebraucht werden.
    """
    return _lese_wpp(
        ROH_WPP / "WPP2024_Demographic_Indicators_Medium.csv.gz",
        WPP_INDIKATOR_SPALTEN,
    )


def lade_wpp_altersgruppen() -> pd.DataFrame:
    """Bevölkerung nach Fünfjahresgruppe und Geschlecht, Stichtag 1. Januar."""
    return _lese_wpp(
        ROH_WPP / "WPP2024_Population1JanuaryByAge5GroupSex_Medium.csv.gz",
        WPP_ALTER_SPALTEN,
    )


# --- WID -------------------------------------------------------------------
def lade_wid_laender() -> pd.DataFrame:
    """Länderliste von WID, reduziert auf echte Länder.

    Echt = `alpha2` hat genau zwei Zeichen. Codes mit Bindestrich sind
    Subregionen (US-CA) oder Wechselkursvarianten von Weltregionen (QB-MER).
    Namibia ("NA") wird wie bei WPP vor der NA-Erkennung geschützt.
    """
    df = pd.read_csv(
        ROH_WID / "WID_countries.csv",
        sep=";",
        keep_default_na=False,
        na_values=[""],
    )
    return df[df["alpha2"].str.len() == 2].reset_index(drop=True)


def lade_wid_daten(
    codes: list[str],
    variablen: list[str] = WID_VARIABLEN,
    perzentile: list[str] = PERZENTILE,
    ausgabe: bool = True,
) -> pd.DataFrame:
    """Liest die WID_data_XX.csv der gegebenen Länder und behält nur die
    benötigten Variablen und Perzentile.

    Nutzt den pyarrow-Parser: etwa fünfmal schneller als der Standardparser,
    bei 423 Dateien zu je 20 MB der Unterschied zwischen einer und fünf Minuten.

    Einige (leere oder alte) Dateien haben keine Spalte `data_quality` — sie
    bekommen die Spalte mit NaN, damit sich alles zusammenfügen lässt.
    """
    spalten = ["country", "variable", "percentile", "year", "value", "data_quality"]
    teile = []
    for code in codes:
        datei = ROH_WID / f"WID_data_{code}.csv"
        if not datei.exists():
            continue
        df = pd.read_csv(datei, sep=";", engine="pyarrow")
        if "data_quality" not in df.columns:
            df["data_quality"] = float("nan")
        df = df[df["variable"].isin(variablen) & df["percentile"].isin(perzentile)]
        teile.append(df[spalten])

    daten = pd.concat(teile, ignore_index=True)
    # Reihen mit NaN-Wert sind Platzhalter, keine Beobachtungen.
    daten = daten.dropna(subset=["value"]).reset_index(drop=True)
    if ausgabe:
        print(
            f"WID: {len(teile)} Dateien gelesen, {len(daten):,} Zeilen behalten "
            f"({daten['country'].nunique()} Länder mit Werten)"
        )
    return daten


def lade_wid_metadaten(codes: list[str], variable: str = VAR_ANTEIL) -> pd.DataFrame:
    """Quelle, Methode und Durchschnittsqualität je Land für eine Variable.

    Die Metadaten-Dateien enthalten mehrzeilige, in Anführungszeichen
    gesetzte Felder — dafür ist der Standardparser robuster als pyarrow.
    """
    spalten = ["country", "variable", "source", "method", "avg_quality"]
    teile = []
    for code in codes:
        datei = ROH_WID / f"WID_metadata_{code}.csv"
        if not datei.exists():
            continue
        df = pd.read_csv(datei, sep=";", low_memory=False)
        if "avg_quality" not in df.columns:
            df["avg_quality"] = float("nan")
        df = df[df["variable"] == variable]
        if not df.empty:
            teile.append(df[spalten])
    return pd.concat(teile, ignore_index=True)
