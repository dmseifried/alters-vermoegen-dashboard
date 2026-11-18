"""
Exportiert die Charts statisch nach `figures/` als PNG und SVG (16:9).

Für die Präsentation: 1280 × 720 Punkte, PNG mit doppelter Auflösung.
Schriftgröße ist in `src/charts.py` auf mindestens 14 pt gesetzt.

Aufruf:  uv run python scripts/export_figures.py
"""

import os
import shutil
import sys
from pathlib import Path

PROJEKT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJEKT))

# kaleido braucht einen Chromium-Browser und findet Chrome/Chromium selbst.
# Nur wenn keiner im PATH liegt, aber Flatpak da ist, nutzen wir den
# Brave-Flatpak-Wrapper. Ein gesetztes BROWSER_PATH hat immer Vorrang.
CHROMIUM = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]
if not any(shutil.which(b) for b in CHROMIUM) and shutil.which("flatpak"):
    os.environ.setdefault(
        "BROWSER_PATH", str(PROJEKT / "scripts" / "kaleido-browser.sh")
    )

import pandas as pd

from src import charts
from src.load import VERARBEITET, VERTIEFUNGSLAENDER

FIGURES = PROJEKT / "figures"
BREITE, HOEHE = 1280, 720  # 16:9
JAHR = 2023  # letztes Beobachtungsjahr (WPP-Schätzung)


def speichern(fig, name: str) -> None:
    """Schreibt PNG (2-fach) und SVG mit festem 16:9-Format."""
    fig.update_layout(width=BREITE, height=HOEHE)
    fig.write_image(FIGURES / f"{name}.png", width=BREITE, height=HOEHE, scale=2)
    fig.write_image(FIGURES / f"{name}.svg", width=BREITE, height=HOEHE)
    print(f"  {name}.png / .svg")


def main() -> None:
    FIGURES.mkdir(exist_ok=True)
    lj = pd.read_parquet(VERARBEITET / "laender_jahr.parquet")
    pyr = pd.read_parquet(VERARBEITET / "pyramide.parquet")

    # Namen und ISO3 der Vertiefungsländer aus den Daten
    laender = lj.drop_duplicates("iso2").set_index("iso2")
    iso3 = {iso2: laender.loc[iso2, "iso3"] for iso2 in VERTIEFUNGSLAENDER}
    namen_iso3 = {iso3[iso2]: name for iso2, name in VERTIEFUNGSLAENDER.items()}

    print("Export nach", FIGURES)
    speichern(charts.pyramide(pyr, iso3["DE"], JAHR, "Deutschland"), "c01_pyramide")
    speichern(
        charts.pyramiden_vergleich(
            pyr, [iso3[c] for c in ["NE", "IN", "US", "JP"]], JAHR, namen_iso3
        ),
        "c02_pyramiden_vergleich",
    )
    speichern(charts.medianalter_karte(lj, JAHR), "c03_medianalter_karte")
    speichern(
        charts.oadr_verlauf(lj, list(VERTIEFUNGSLAENDER), VERTIEFUNGSLAENDER),
        "c04_oadr",
    )

    # Vermögen (WID) — jeder Chart einzeln abgesichert, damit ein Fehler
    # nicht den ganzen Export stoppt
    dez = pd.read_parquet(VERARBEITET / "wid_dezile.parquet")
    q = pd.read_parquet(VERARBEITET / "wid_qualitaet.parquet")
    vl = list(VERTIEFUNGSLAENDER)
    auftraege = [
        ("c05_top10_verlauf", lambda: charts.top10_verlauf(lj, vl, VERTIEFUNGSLAENDER)),
        ("c06_lorenz", lambda: charts.lorenzkurven(dez, vl, JAHR, VERTIEFUNGSLAENDER)),
        (
            "c07_median_mittel",
            lambda: charts.median_mittel_dumbbell(lj, vl, JAHR, VERTIEFUNGSLAENDER),
        ),
        (
            "c08_scatter",
            lambda: charts.scatter_alter_vermoegen(lj, JAHR, VERTIEFUNGSLAENDER),
        ),
        (
            "c08_scatter_2017",
            lambda: charts.scatter_alter_vermoegen(lj, 2017, VERTIEFUNGSLAENDER),
        ),
        ("c09_qualitaet_region", lambda: charts.qualitaet_nach_region(q)),
        ("c10_bruch_frankreich", lambda: charts.bruch_frankreich(lj)),
    ]
    fehler = []
    for name, bauen in auftraege:
        try:
            speichern(bauen(), name)
        except Exception as e:  # noqa: BLE001 — bewusst: Export soll weiterlaufen
            fehler.append((name, repr(e)))
            print(f"  FEHLER {name}: {e!r}")
    if fehler:
        print(f"{len(fehler)} Chart(s) nicht exportiert:", [n for n, _ in fehler])


if __name__ == "__main__":
    main()
