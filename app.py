"""
Streamlit-Dashboard: Alters- und Vermögensverteilungen international.

Vier Tabs entlang der Dramaturgie (Spezifikation Abschnitt 6, Phase 3):
1. Demografie (C1–C4), 2. Vermögen (C5–C7), 3. Zusammenhang (C8),
4. Datenqualität & Methodik (C9, C10, Quellen, Limitationen).

Liest ausschließlich aus `data/processed/` (erzeugt mit
`uv run python -m src.clean`). Aufruf:  uv run streamlit run app.py
"""

import pandas as pd
import streamlit as st

from src import charts
from src.clean import JAHR_BIS, JAHR_VON, PROJEKTION_AB
from src.load import BELASTBAR, QUELLE_WID, QUELLE_WPP, VERARBEITET, VERTIEFUNGSLAENDER

st.set_page_config(page_title="Alter und Vermögen international", layout="wide")

WID_BIS = 2024  # letztes WID-Jahr
BEOBACHTUNG_BIS = PROJEKTION_AB - 1  # letztes WPP-Beobachtungsjahr (2023)


# --- Daten -------------------------------------------------------------------
@st.cache_data
def lade(name: str) -> pd.DataFrame:
    """Liest eine aufbereitete Parquet-Datei, einmal pro Sitzung."""
    return pd.read_parquet(VERARBEITET / f"{name}.parquet")


def zeige(fig) -> None:
    """Einheitliche Chart-Ausgabe (volle Breite, Höhe 16:9-nah)."""
    fig.update_layout(height=560)
    st.plotly_chart(fig, width="stretch")


fehlend = [n for n in ["laender_jahr", "pyramide", "wid_dezile", "wid_qualitaet"]
           if not (VERARBEITET / f"{n}.parquet").exists()]  # fmt: skip
if fehlend:
    st.error(
        f"Aufbereitete Daten fehlen ({', '.join(fehlend)}). "
        "Erst `uv run python -m src.clean` ausführen."
    )
    st.stop()

lj = lade("laender_jahr")
pyr = lade("pyramide")
dez = lade("wid_dezile")
qual = lade("wid_qualitaet")

# Länderliste: alle WPP-Länder, deutsche Namen wo vorhanden
laender = lj.drop_duplicates("iso2").set_index("iso2")
namen = {iso2: charts.name_de(iso2, z["land"]) for iso2, z in laender.iterrows()}
iso3_von = laender["iso3"].to_dict()
mit_wid = set(lj.dropna(subset=["top10"])["iso2"])

# --- Sidebar -------------------------------------------------------------------
st.sidebar.title("Alter und Vermögen")
auswahl = st.sidebar.multiselect(
    "Länder",
    options=sorted(namen, key=lambda i: namen[i]),
    default=list(VERTIEFUNGSLAENDER),
    format_func=lambda i: namen[i] + ("" if i in mit_wid else " (ohne Vermögensdaten)"),
    max_selections=8,
)
jahr = st.sidebar.slider(
    "Jahr", min_value=JAHR_VON, max_value=JAHR_BIS, value=BEOBACHTUNG_BIS, step=1,
    help=f"Ab {PROJEKTION_AB}: UN-Projektion (Medium). Vermögensdaten reichen bis {WID_BIS}.",
)  # fmt: skip
nur_belastbar = st.sidebar.toggle(
    f"nur belastbare Werte (Qualität ≥ {BELASTBAR})",
    value=False,
    help="Wirkt in allen Vermögens-Charts. Geschätzte Werte (Imputation) werden ausgeblendet.",
)
jahr_wid = min(jahr, WID_BIS)
if jahr > WID_BIS:
    st.sidebar.caption(f"Vermögens-Charts zeigen {WID_BIS} (letztes WID-Jahr).")
st.sidebar.markdown("---")
st.sidebar.caption(f"Quellen: {QUELLE_WPP}; {QUELLE_WID}.")

namen_auswahl = {i: namen[i] for i in auswahl}
auswahl_wid = [i for i in auswahl if i in mit_wid]

# --- Tabs ------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "1 · Demografie",
        "2 · Vermögen",
        "3 · Zusammenhang",
        "4 · Datenqualität & Methodik",
    ]
)

with tab1:
    st.subheader("Die Welt altert — sehr ungleich")
    if not auswahl:
        st.info("Bitte links mindestens ein Land wählen.")
    else:
        land_c1 = st.selectbox("Land für die Pyramide", auswahl, format_func=namen.get)
        zeige(charts.pyramide(pyr, iso3_von[land_c1], jahr, namen[land_c1]))
        vergleich = auswahl[:4]
        if len(vergleich) >= 2:
            zeige(charts.pyramiden_vergleich(
                pyr, [iso3_von[i] for i in vergleich], jahr,
                {iso3_von[i]: namen[i] for i in vergleich},
            ))  # fmt: skip
            if len(auswahl) > 4:
                st.caption("Der Vergleich zeigt die ersten vier gewählten Länder.")
    zeige(charts.medianalter_karte(lj, jahr))
    if auswahl:
        zeige(charts.oadr_verlauf(lj, auswahl, namen_auswahl))

with tab2:
    st.subheader("Vermögen ist ungleicher verteilt als Alter")
    if not auswahl_wid:
        st.info("Keines der gewählten Länder hat Vermögensdaten.")
    else:
        try:
            zeige(charts.top10_verlauf(lj, auswahl_wid, namen_auswahl, nur_belastbar))
        except ValueError as e:
            st.warning(str(e))
        try:
            zeige(
                charts.lorenzkurven(
                    dez, auswahl_wid, jahr_wid, namen_auswahl, nur_belastbar
                )
            )
        except ValueError:
            st.warning(
                f"Keine Lorenzkurve für {jahr_wid}"
                + (" mit belastbaren Werten." if nur_belastbar else ".")
            )
        if nur_belastbar:
            st.info(
                "Median vs. Mittelwert wird nicht gezeigt: für 2023 sind alle "
                f"Vermögenswerte geschätzt (letzte Messung 2022, Qualität ≥ {BELASTBAR} "
                "nur bis dahin)."
            )
        else:
            zeige(charts.median_mittel_dumbbell(lj, auswahl_wid, 2023, namen_auswahl))

with tab3:
    st.subheader("Der Zusammenhang zwischen beidem")
    try:
        zeige(
            charts.scatter_alter_vermoegen(lj, jahr_wid, namen_auswahl, nur_belastbar)
        )
    except (ValueError, KeyError):
        st.warning(f"Keine Daten für {jahr_wid} mit dieser Einstellung.")
    if jahr_wid > 2022:
        st.caption(
            f"Für {jahr_wid} ist jeder Wert geschätzt; belastbare Werte gibt es bis 2022. "
            "Jahr links auf 2017 stellen, um gemessene und geschätzte Länder zu unterscheiden."
        )
    st.caption(
        "Keine Regressionslinie: Ländermittelwerte erlauben keine Aussage über Personen "
        "(ökologischer Fehlschluss)."
    )

with tab4:
    st.subheader("Die Wendung: Wie viel davon ist gemessen?")
    zeige(charts.qualitaet_nach_region(qual))
    zeige(charts.bruch_frankreich(lj))

    st.markdown("### Quellen")
    st.markdown(
        f"""
- **Alter:** {QUELLE_WPP}. Dateien `WPP2024_Demographic_Indicators_Medium` (Stichtag 1. Juli)
  und `WPP2024_Population1JanuaryByAge5GroupSex_Medium` (Stichtag 1. Januar).
- **Vermögen:** {QUELLE_WID}. Variablen `shwealj992` (Anteile), `ahwealj992`
  (Durchschnitt), `thwealj992` (Schwellen, Median = `p50p100`), `xlcuspi999` (PPP).
  Netto-Privatvermögen, equal-split adults ab 20.
- **Qualitätsscore:** WID `data_quality`, Skala 0–5 je Land, Reihe und Jahr;
  belastbar = ≥ {BELASTBAR}. Viele Länder haben als einzige Quelle das Imputationspapier
  (Bajard et al. 2021/2025, *Global Wealth Inequality on WID.world: Estimates and
  Imputations*).
"""
    )
    st.markdown("### Limitationen")
    st.markdown(
        f"""
- **Imputation.** {int((~qual["hat_daten"]).sum())} der 241 WID-Länder haben keine
  Vermögensreihe; von den übrigen erreichten nur {int((qual["max_quality"] >= BELASTBAR).sum())}
  je Qualität ≥ {BELASTBAR}, kein Land nach 2022. Alle Werte für 2023/2024 sind Schätzungen.
- **Ökologischer Fehlschluss.** Alle Kennzahlen sind Ländermittelwerte. Ein Zusammenhang
  zwischen Medianalter und Vermögenskonzentration auf Länderebene sagt nichts über
  einzelne Personen.
- **Stichtage.** WPP-Indikatoren (Medianalter, Bevölkerung) gelten zum 1. Juli,
  Altersgruppen und der daraus berechnete Altersabhängigkeitsquotient zum 1. Januar.
- **Projektionen.** Werte ab {PROJEKTION_AB} sind die UN-Medium-Variante, ein Szenario
  unter vielen; in den Charts gestrichelt.
- **PPP-Umrechnung.** Vermögen in Kaufkraftdollar nur in „Median vs. Mittelwert",
  umgerechnet mit einer Rate je Land (Preisbasisjahr 2025). Bei langen Reihen verzerren
  wandernde Preisniveaus, ein fester Warenkorb und der Einkommens- statt
  Vermögensdeflator; Anteile sind davon unberührt.
- **Regionen** folgen der UN-Gliederung (WPP). Zypern zählt zu Asien, Belarus, Russland
  und Ukraine zu Europa — anders als bei WID.
"""
    )
