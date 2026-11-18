"""
Charts für Dashboard und Präsentation — eine Funktion pro Chart.

Jede Funktion bekommt einen DataFrame aus `data/processed/` und gibt eine
`go.Figure` zurück. Kein `fig.show()`, keine Dateiausgabe. Gestaltung nach
`docs/visualisierungsregeln.md`:

- Titel als Aussage (mit Zahlen aus den Daten), Untertitel beschreibt Inhalt
- Achsen mit Einheit, Quelle und Abrufdatum als Fußzeile
- deutsche Zahlenformate (Dezimalkomma, Tausenderpunkt)
- Okabe-Ito für Kategorien, viridis für Werte
- Projektionen gestrichelt und durch eine Trennlinie abgesetzt
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.load import BELASTBAR, QUELLE_WID, QUELLE_WPP, VERTIEFUNGSLAENDER

# --- Gestaltungskonstanten ---------------------------------------------------
# Okabe-Ito: farbfehlsichtigkeitssicher (Wilke, Kap. 19). Gelb (#F0E442) ist
# auf Weiß kaum lesbar und wird für Linien nicht verwendet; stattdessen das
# Grau der ursprünglichen 9-Farben-Fassung.
OKABE_ITO = {
    "orange": "#E69F00",
    "hellblau": "#56B4E9",
    "gruen": "#009E73",
    "gelb": "#F0E442",
    "blau": "#0072B2",
    "rotorange": "#D55E00",
    "rosa": "#CC79A7",
    "schwarz": "#000000",
    "grau": "#999999",
}

# Feste Farbe je Vertiefungsland — Farbe folgt dem Land, nicht der Reihenfolge,
# damit ein Land in jedem Chart gleich aussieht. Zugeordnet so, dass Linien,
# die in C4 nebeneinander enden, verschiedene Farben haben.
FARBEN_LAENDER = {
    "FR": OKABE_ITO["orange"],
    "US": OKABE_ITO["hellblau"],
    "DE": OKABE_ITO["blau"],
    "IN": OKABE_ITO[
        "grau"
    ],  # 8 Länder, 7 lesbare Farben: Indien ist in keinem Chart Extremwert
    "CN": OKABE_ITO["gruen"],
    "JP": OKABE_ITO["schwarz"],
    "NE": OKABE_ITO["rosa"],
    "ZA": OKABE_ITO["rotorange"],
}
FARBE_MAENNER = OKABE_ITO["blau"]
FARBE_FRAUEN = OKABE_ITO["orange"]
GRAU = "#6b6b6b"
GRAU_HELL = "#d9d9d9"
SCHRIFT = "Arial, Helvetica, sans-serif"
SCHRIFTGROESSE = 14  # Minimum laut Regeln (Präsentation)

PROJEKTION_AB = 2024  # WPP: ab hier Medium-Projektion

ALTERSGRUPPEN = [
    "0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39", "40-44",
    "45-49", "50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80-84",
    "85-89", "90-94", "95-99", "100+",
]  # fmt: skip

# Deutsche Ländernamen für Titel. WPP liefert englische Namen; übersetzt sind
# nur die Vertiefungsländer und Länder, die in Titeln als Extremwerte auftauchen.
# Alles andere bleibt englisch (Hover, Tabellen).
LAND_DE = VERTIEFUNGSLAENDER | {
    "CF": "Zentralafrikanische Republik",
    "TD": "Tschad",
    "SO": "Somalia",
    "ML": "Mali",
    "IT": "Italien",
    "KR": "Südkorea",
    "HK": "Hongkong",
    "ES": "Spanien",
    "GR": "Griechenland",
    "PT": "Portugal",
}


# --- Hilfsfunktionen ---------------------------------------------------------
def de(zahl: float, nachkomma: int = 0) -> str:
    """Formatiert eine Zahl deutsch: 1.234,5. Für Titel und Annotationen."""
    text = f"{zahl:,.{nachkomma}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def name_de(iso2: str, fallback: str) -> str:
    """Deutscher Ländername, falls bekannt, sonst der WPP-Name."""
    return LAND_DE.get(iso2, fallback)


def basis_layout(
    fig: go.Figure,
    titel: str,
    untertitel: str,
    quelle: str,
    fuss_abstand: int = 95,
    rand_unten: int = 125,
) -> go.Figure:
    """Einheitliches Layout: Titel + Untertitel, Fußzeile mit Quelle,
    deutsche Trennzeichen, zurückhaltendes Gitter, weißer Hintergrund.

    Die Fußzeile sitzt `fuss_abstand` Pixel unter dem Plotbereich (Platz für
    Achsenticks und Achsentitel); `rand_unten` ist der Rand, der dafür
    freigehalten wird.
    """
    fig.update_layout(
        title={
            "text": f"{titel}<br><span style='font-size:{SCHRIFTGROESSE}px;color:{GRAU}'>"
            f"{untertitel}</span>",
            "x": 0.0,
            "xanchor": "left",
            "y": 0.95,
            "yanchor": "top",
            "font": {"size": 20},
        },
        font={"family": SCHRIFT, "size": SCHRIFTGROESSE, "color": "#222"},
        separators=",.",  # Dezimalkomma, Tausenderpunkt
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin={"l": 70, "r": 40, "t": 110, "b": rand_unten},
        hoverlabel={"font": {"family": SCHRIFT, "size": SCHRIFTGROESSE}},
    )
    fig.update_xaxes(
        showgrid=False, zeroline=False, linecolor=GRAU_HELL, ticks="outside"
    )
    fig.update_yaxes(gridcolor=GRAU_HELL, zeroline=False, linecolor="white")
    fig.add_annotation(
        text=f"Quelle: {quelle}", name="quelle",
        xref="paper", yref="paper", x=0, y=0, xanchor="left", yanchor="top",
        yshift=-fuss_abstand, showarrow=False,
        font={"size": SCHRIFTGROESSE - 2, "color": GRAU},
    )  # fmt: skip
    return fig


def _pyramide_daten(pyr: pd.DataFrame, iso3: str, jahr: int) -> pd.DataFrame:
    """Anteile je Altersgruppe und Geschlecht für ein Land und Jahr,
    in der Reihenfolge der Altersgruppen."""
    d = pyr[(pyr["iso3"] == iso3) & (pyr["jahr"] == jahr)]
    if d.empty:
        raise ValueError(f"Keine Pyramidendaten für {iso3} {jahr}")
    breit = d.pivot(index="altersgruppe", columns="geschlecht", values="anteil")
    return breit.reindex(ALTERSGRUPPEN)


def _anteile_jung_alt(breit: pd.DataFrame) -> tuple[float, float]:
    """Anteil unter 15 und Anteil 65+ (beide Geschlechter), in Prozent."""
    gesamt = breit["m"] + breit["w"]
    unter15 = gesamt.loc[["0-4", "5-9", "10-14"]].sum() * 100
    ab65 = gesamt.loc["65-69":].sum() * 100
    return unter15, ab65


def _pyramide_spuren(breit: pd.DataFrame) -> list[go.Bar]:
    """Zwei Balkenspuren: Männer nach links (negativ), Frauen nach rechts."""
    return [
        go.Bar(
            y=breit.index, x=-breit["m"] * 100, orientation="h",
            name="Männer", marker_color=FARBE_MAENNER,
            customdata=breit["m"] * 100,
            hovertemplate="Männer %{y}: %{customdata:.1f} %<extra></extra>",
        ),
        go.Bar(
            y=breit.index, x=breit["w"] * 100, orientation="h",
            name="Frauen", marker_color=FARBE_FRAUEN,
            hovertemplate="Frauen %{y}: %{x:.1f} %<extra></extra>",
        ),
    ]  # fmt: skip


def _pyramide_achse(maximum: float) -> dict:
    """Symmetrische x-Achse, beidseitig positiv beschriftet (keine Minuszeichen)."""
    schritt = 1 if maximum <= 4 else 2 if maximum <= 8 else 5
    ticks = list(range(0, int(maximum) + 1, schritt))
    return {
        "range": [-maximum, maximum],
        "tickvals": [-t for t in ticks[::-1]] + ticks[1:],
        "ticktext": [f"{t} %" for t in ticks[::-1]] + [f"{t} %" for t in ticks[1:]],
        "title": "Anteil an der Gesamtbevölkerung",
    }


def _projektionshinweis(jahr: int) -> str:
    return " — Projektion (UN Medium-Variante)" if jahr >= PROJEKTION_AB else ""


# --- C1: Bevölkerungspyramide ------------------------------------------------
def pyramide(
    pyr: pd.DataFrame, iso3: str, jahr: int, land: str | None = None
) -> go.Figure:
    """C1 — Wie ist die Altersstruktur eines Landes in einem Jahr?

    Divergierende horizontale Balken, Männer links, Frauen rechts, relative
    Anteile an der Gesamtbevölkerung. Stichtag der Altersdaten: 1. Januar.
    """
    land = land or iso3
    breit = _pyramide_daten(pyr, iso3, jahr)
    unter15, ab65 = _anteile_jung_alt(breit)
    maximum = max(breit["m"].max(), breit["w"].max()) * 100 * 1.1

    fig = go.Figure(_pyramide_spuren(breit))
    fig.update_layout(
        barmode="overlay",
        bargap=0.15,
        legend={
            "orientation": "h",
            "x": 1,
            "xanchor": "right",
            "y": 1.02,
            "yanchor": "bottom",
        },
    )
    fig.update_xaxes(**_pyramide_achse(maximum))
    fig.update_yaxes(
        title="Altersgruppe (Jahre)", categoryorder="array", categoryarray=ALTERSGRUPPEN
    )
    return basis_layout(
        fig,
        titel=f"{land} {jahr}: {de(unter15, 1)} % unter 15, {de(ab65, 1)} % ab 65",
        untertitel="Bevölkerung nach Alter und Geschlecht, Stichtag 1. Januar"
        + _projektionshinweis(jahr),
        quelle=QUELLE_WPP,
    )


# --- C2: Pyramiden-Vergleich (Small Multiples) --------------------------------
def pyramiden_vergleich(
    pyr: pd.DataFrame, iso3s: list[str], jahr: int, namen: dict[str, str] | None = None
) -> go.Figure:
    """C2 — Wie unterschiedlich altern Länder?

    Vier Pyramiden nebeneinander mit gemeinsamer Skala, sortiert von jung
    nach alt (Anteil unter 15 absteigend), damit der Vergleich trägt.
    """
    namen = namen or {}
    daten = {iso3: _pyramide_daten(pyr, iso3, jahr) for iso3 in iso3s}
    kennzahlen = {iso3: _anteile_jung_alt(b) for iso3, b in daten.items()}
    reihenfolge = sorted(iso3s, key=lambda i: -kennzahlen[i][0])
    maximum = max(max(b["m"].max(), b["w"].max()) for b in daten.values()) * 100 * 1.1

    fig = make_subplots(
        rows=1, cols=len(reihenfolge), shared_yaxes=True, horizontal_spacing=0.03,
        subplot_titles=[
            f"<b>{namen.get(i, i)}</b><br><span style='font-size:{SCHRIFTGROESSE - 1}px;"
            f"color:{GRAU}'>unter 15: {de(kennzahlen[i][0], 0)} % · "
            f"ab 65: {de(kennzahlen[i][1], 0)} %</span>"
            for i in reihenfolge
        ],
    )  # fmt: skip
    achse = _pyramide_achse(maximum)
    achse["title"] = None  # ein gemeinsamer Achsentitel unter allen Panels
    for spalte, iso3 in enumerate(reihenfolge, start=1):
        for spur in _pyramide_spuren(daten[iso3]):
            spur.showlegend = spalte == 1  # eine gemeinsame Legende
            fig.add_trace(spur, row=1, col=spalte)
        fig.update_xaxes(**achse, row=1, col=spalte)
    fig.update_yaxes(categoryorder="array", categoryarray=ALTERSGRUPPEN)
    fig.update_yaxes(title="Altersgruppe (Jahre)", row=1, col=1)
    fig.update_layout(
        barmode="overlay",
        bargap=0.15,
        legend={
            "orientation": "h",
            "x": 1,
            "xanchor": "right",
            "y": 1.2,
            "yanchor": "bottom",
        },
    )
    # Panel-Überschriften etwas höher, damit sie nicht an den Balken kleben
    fig.update_annotations(yshift=8, selector={"xref": "paper"})
    fig.add_annotation(
        text="Anteil an der Gesamtbevölkerung", xref="paper", yref="paper",
        x=0.5, y=0, xanchor="center", yanchor="top", yshift=-48, showarrow=False,
    )  # fmt: skip
    jung, alt = reihenfolge[0], reihenfolge[-1]
    fig = basis_layout(
        fig,
        titel=f"{namen.get(jung, jung)}: {de(kennzahlen[jung][0], 0)} % unter 15 — "
        f"{namen.get(alt, alt)}: {de(kennzahlen[alt][1], 0)} % ab 65",
        untertitel=f"Altersstruktur {jahr}, gemeinsame Skala, sortiert von jung nach alt"
        + _projektionshinweis(jahr),
        quelle=QUELLE_WPP,
        fuss_abstand=80,
    )
    fig.update_layout(margin={"t": 180}, title={"y": 0.97})
    return fig


# --- C3: Medianalter-Karte ---------------------------------------------------
def medianalter_karte(lj: pd.DataFrame, jahr: int) -> go.Figure:
    """C3 — Wo ist die Welt alt, wo jung?

    Choropleth in Equal-Earth-Projektion (flächentreu), sequenzielle
    viridis-Skala mit festem Wertebereich, damit Jahre vergleichbar bleiben.
    Länder ohne Wert erscheinen grau. Der Titel nennt die Extreme unter den
    Ländern ab einer Million Einwohnern (sonst Kleinststaaten wie der
    Heilige Stuhl).
    """
    d = lj[lj["jahr"] == jahr].dropna(subset=["medianalter"])
    gross = d[d["bevoelkerung_tsd"] >= 1000]
    juengstes = gross.loc[gross["medianalter"].idxmin()]
    aeltestes = gross.loc[gross["medianalter"].idxmax()]

    fig = go.Figure(
        go.Choropleth(
            locations=d["iso3"],
            z=d["medianalter"],
            text=d["land"],
            colorscale="Viridis",
            zmin=15,
            zmax=50,
            marker_line_color="white",
            marker_line_width=0.4,
            colorbar={
                "title": {"text": "Medianalter in Jahren", "side": "right"},
                "thickness": 14,
                "len": 0.7,
            },
            hovertemplate="%{text}<br>Medianalter: %{z:.1f} Jahre<extra></extra>",
        )
    )
    fig.update_geos(
        projection_type="equal earth",
        showframe=False,
        showcoastlines=False,
        showcountries=False,
        landcolor="#e6e6e6",  # Länder ohne Wert
        showland=True,
        showocean=False,
        showlakes=False,
        bgcolor="white",
    )
    fig = basis_layout(
        fig,
        titel=f"{jahr}: Medianalter von {de(juengstes['medianalter'], 0)} Jahren "
        f"({name_de(juengstes['iso2'], juengstes['land'])}) bis "
        f"{de(aeltestes['medianalter'], 0)} ({name_de(aeltestes['iso2'], aeltestes['land'])})",
        untertitel="Medianalter der Bevölkerung, Stichtag 1. Juli; Länder ab 1 Mio. Einwohnern "
        "im Titel; Projektion Equal Earth (flächentreu)" + _projektionshinweis(jahr),
        quelle=QUELLE_WPP + ". Grau: kein Wert.",
        fuss_abstand=10,
        rand_unten=50,
    )
    fig.update_layout(margin={"l": 10, "r": 10})
    return fig


# --- C4: Altersabhängigkeitsquotient 1990–2050 --------------------------------
def oadr_verlauf(
    lj: pd.DataFrame, iso2s: list[str], namen: dict[str, str] | None = None
) -> go.Figure:
    """C4 — Wie entwickelt sich die Alterslast?

    Personen ab 65 je 100 Personen im Alter 15–64. Beobachtung bis 2023
    durchgezogen, Projektion ab 2024 gestrichelt, Trennlinie dazwischen.
    Direkte Beschriftung am Linienende statt Legende.
    """
    namen = namen or {}
    d = lj[lj["iso2"].isin(iso2s) & lj["jahr"].between(1990, 2050)].copy()
    d["oadr_100"] = d["oadr"] * 100

    fig = go.Figure()
    endwerte = []
    ersatzfarben = [f for f in OKABE_ITO.values() if f != OKABE_ITO["gelb"]]
    for i, iso2 in enumerate(iso2s):
        land = d[d["iso2"] == iso2].sort_values("jahr")
        farbe = FARBEN_LAENDER.get(iso2, ersatzfarben[i % len(ersatzfarben)])
        name = namen.get(iso2, iso2)
        beob = land[land["jahr"] < PROJEKTION_AB]
        proj = land[
            land["jahr"] >= PROJEKTION_AB - 1
        ]  # ab 2023, damit die Linie anschließt
        fig.add_trace(go.Scatter(
            x=beob["jahr"], y=beob["oadr_100"], mode="lines", name=name,
            line={"color": farbe, "width": 2.5}, legendgroup=name, showlegend=False,
            hovertemplate=f"{name} %{{x}}: %{{y:.0f}} je 100<extra></extra>",
        ))  # fmt: skip
        fig.add_trace(go.Scatter(
            x=proj["jahr"], y=proj["oadr_100"], mode="lines", name=name,
            line={"color": farbe, "width": 2.5, "dash": "dash"}, legendgroup=name,
            showlegend=False,
            hovertemplate=f"{name} %{{x}} (Projektion): %{{y:.0f}} je 100<extra></extra>",
        ))  # fmt: skip
        endwerte.append((land["oadr_100"].iloc[-1], name, farbe))

    # Direkte Beschriftung rechts, mit Mindestabstand gegen Überlappung
    endwerte.sort()
    y_max = d["oadr_100"].max() * 1.1
    mindestabstand = y_max * 0.045
    positionen = []
    for wert, name, farbe in endwerte:
        y = wert if not positionen else max(wert, positionen[-1] + mindestabstand)
        positionen.append(y)
        fig.add_annotation(
            x=2050, y=y, text=name, xanchor="left", xshift=6, showarrow=False,
            font={"color": farbe, "size": SCHRIFTGROESSE},
        )  # fmt: skip

    # Trennlinie Beobachtung | Projektion
    fig.add_vline(
        x=PROJEKTION_AB - 0.5, line={"color": GRAU, "width": 1, "dash": "dot"}
    )
    fig.add_annotation(
        x=PROJEKTION_AB - 0.5, y=y_max, text="ab 2024 Projektion (UN Medium-Variante)",
        xanchor="left", xshift=4, yanchor="top", showarrow=False,
        font={"color": GRAU, "size": SCHRIFTGROESSE - 1},
    )  # fmt: skip

    spitze = max(endwerte)
    fig.update_xaxes(title="Jahr", range=[1990, 2050 + 7], dtick=10)
    fig.update_yaxes(
        title="Personen ab 65 je 100 Personen im Alter 15–64", range=[0, y_max]
    )
    return basis_layout(
        fig,
        titel=f"{spitze[1]}: 2050 kommen {de(spitze[0], 0)} Ältere auf 100 Personen "
        "im Erwerbsalter",
        untertitel="Altersabhängigkeitsquotient 1990–2050, Bevölkerung 65+ geteilt durch 15–64, "
        "Stichtag 1. Januar",
        quelle=QUELLE_WPP,
    )


# =============================================================================
# Vermögen (WID)
# =============================================================================
FARBEN_REGION = {
    "Afrika": OKABE_ITO["orange"],
    "Amerika": OKABE_ITO["hellblau"],
    "Asien": OKABE_ITO["gruen"],
    "Europa": OKABE_ITO["blau"],
    "Ozeanien": OKABE_ITO["rosa"],
}
# Sequenzielle Farben für Qualitätsstufen 0–5 (viridis, gestuft) + „keine Daten"
FARBEN_QUALITAET = ["#fde725", "#addc30", "#5ec962", "#21918c", "#3b528b", "#440154"]
FARBE_KEINE_DATEN = "#cccccc"
HINWEIS_BELASTBAR = f"belastbar = WID-Qualität ≥ {BELASTBAR} (durchgezogen), sonst geschätzt (gestrichelt, hell)"


def _laeufe(land: pd.DataFrame) -> list[tuple[bool, pd.DataFrame]]:
    """Zerlegt eine Zeitreihe in zusammenhängende Abschnitte gleicher
    Belastbarkeit. Jeder Abschnitt nimmt den ersten Punkt des nächsten mit,
    damit die Linie ohne Lücke weiterläuft."""
    land = land.sort_values("jahr").reset_index(drop=True)
    flag = (land["quality_top10"] >= BELASTBAR).to_numpy()
    laeufe, start = [], 0
    for i in range(1, len(land) + 1):
        if i == len(land) or flag[i] != flag[start]:
            ende = min(i + 1, len(land))  # Anschlusspunkt mitnehmen
            laeufe.append((bool(flag[start]), land.iloc[start:ende]))
            start = i
    return laeufe


def _linie_mit_qualitaet(
    fig: go.Figure,
    land: pd.DataFrame,
    name: str,
    farbe: str,
    spalte: str,
    einheit: str,
    nur_belastbar: bool = False,
    row: int | None = None,
    col: int | None = None,
) -> None:
    """Zeichnet eine Reihe: belastbare Abschnitte durchgezogen, geschätzte
    gestrichelt und aufgehellt. Mit `nur_belastbar` fallen geschätzte Werte
    weg und hinterlassen Lücken."""
    for belastbar, teil in _laeufe(land):
        if nur_belastbar and not belastbar:
            continue
        fig.add_trace(go.Scatter(
            x=teil["jahr"], y=teil[spalte], mode="lines", name=name, legendgroup=name,
            showlegend=False,
            line={"color": farbe, "width": 2.5 if belastbar else 2,
                  "dash": "solid" if belastbar else "dash"},
            opacity=1.0 if belastbar else 0.65,
            customdata=teil["quality_top10"],
            hovertemplate=f"{name} %{{x}}: %{{y:{einheit}}} · Qualität %{{customdata:.0f}}"
                          "<extra></extra>",
        ), row=row, col=col)  # fmt: skip


def _endbeschriftung(
    fig: go.Figure,
    endwerte: list[tuple[float, str, str]],
    x: float,
    y_spanne: float,
    xref: str = "x",
    yref: str = "y",
) -> None:
    """Direkte Beschriftung am rechten Linienende mit Mindestabstand."""
    endwerte = sorted(endwerte)
    mindestabstand = y_spanne * 0.045
    positionen = []
    for wert, name, farbe in endwerte:
        y = wert if not positionen else max(wert, positionen[-1] + mindestabstand)
        positionen.append(y)
        fig.add_annotation(
            x=x, y=y, xref=xref, yref=yref, text=name, xanchor="left", xshift=6,
            showarrow=False, font={"color": farbe, "size": SCHRIFTGROESSE},
        )  # fmt: skip


# --- C5: Vermögensanteile im Zeitverlauf ---------------------------------------
def top10_verlauf(
    lj: pd.DataFrame,
    iso2s: list[str],
    namen: dict[str, str] | None = None,
    nur_belastbar: bool = False,
) -> go.Figure:
    """C5 — Wie konzentriert ist Vermögen, und wie sicher wissen wir das?

    Anteil der reichsten 10 % am Netto-Privatvermögen je Vertiefungsland,
    1975–2024. Abschnitte mit Qualität < 3 gestrichelt und aufgehellt.
    """
    namen = namen or {}
    d = lj[lj["iso2"].isin(iso2s)].dropna(subset=["top10"]).copy()
    d["top10_pct"] = d["top10"] * 100
    fig = go.Figure()
    endwerte = []
    geschaetzt = {}  # Name -> ist der letzte Wert geschätzt (Qualität < 3)?
    ersatz = [f for f in OKABE_ITO.values() if f != OKABE_ITO["gelb"]]
    for i, iso2 in enumerate(iso2s):
        land = d[d["iso2"] == iso2]
        if land.empty:
            continue
        farbe = FARBEN_LAENDER.get(iso2, ersatz[i % len(ersatz)])
        name = namen.get(iso2, iso2)
        _linie_mit_qualitaet(fig, land, name, farbe, "top10_pct", ".1f", nur_belastbar)
        letzte = land.sort_values("jahr").iloc[-1]
        endwerte.append((letzte["top10_pct"], name, farbe))
        geschaetzt[name] = bool(letzte["quality_top10"] < BELASTBAR)

    y_max = min(100, d["top10_pct"].max() * 1.08)
    y_min = max(0, d["top10_pct"].min() * 0.9)
    _endbeschriftung(fig, endwerte, x=d["jahr"].max(), y_spanne=y_max - y_min)
    spitze = max(endwerte)
    tief = min(endwerte)
    # Geschätzte Werte im Titel kennzeichnen, damit sie nicht als Befund gelesen werden
    n_geschaetzt = geschaetzt[tief[1]] + geschaetzt[spitze[1]]
    kennzeichnung = {2: " — beide Werte geschätzt", 1: " — ein Wert geschätzt", 0: ""}[
        n_geschaetzt
    ]
    fig.update_xaxes(
        title="Jahr", range=[d["jahr"].min(), d["jahr"].max() + 7], dtick=10
    )
    fig.update_yaxes(
        title="Vermögensanteil der reichsten 10 % (%)", range=[y_min, y_max]
    )
    return basis_layout(
        fig,
        titel=f"Die reichsten 10 % halten {de(tief[0], 0)} % ({tief[1]}) bis "
        f"{de(spitze[0], 0)} % ({spitze[1]}) des Vermögens{kennzeichnung}",
        untertitel=f"Anteil am Netto-Privatvermögen, Erwachsene ab 20; {HINWEIS_BELASTBAR}",
        quelle=QUELLE_WID,
    )


# --- C6: Lorenzkurven --------------------------------------------------------
def gini_aus_dezilen(anteile: pd.Series) -> float:
    """Gini-Koeffizient aus zehn Dezilanteilen (Trapezregel unter der
    Lorenzkurve). Negative Anteile (Schulden) sind zulässig."""
    kum = anteile.cumsum().to_numpy()
    y = [0.0, *kum]
    flaeche = sum((y[i] + y[i - 1]) / 2 * 0.1 for i in range(1, len(y)))
    return 1 - 2 * flaeche


def lorenzkurven(
    dez: pd.DataFrame,
    iso2s: list[str],
    jahr: int,
    namen: dict[str, str] | None = None,
    nur_belastbar: bool = False,
) -> go.Figure:
    """C6 — Wie ungleich ist Vermögen insgesamt verteilt?

    Lorenzkurven aus Dezilanteilen, 1:1-Seitenverhältnis, Diagonale als
    Gleichverteilung, Gini als Annotation. Kurven mit Qualität < 3 gestrichelt.
    """
    namen = namen or {}
    d = dez[dez["iso2"].isin(iso2s) & (dez["jahr"] == jahr)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[0, 100], y=[0, 100], mode="lines", name="Gleichverteilung",
        line={"color": GRAU_HELL, "width": 1.5}, hoverinfo="skip", showlegend=False,
    ))  # fmt: skip
    ginis = []
    n_belastbar = 0
    ersatz = [f for f in OKABE_ITO.values() if f != OKABE_ITO["gelb"]]
    for i, iso2 in enumerate(iso2s):
        land = d[d["iso2"] == iso2].sort_values("dezil")
        if len(land) != 10:
            continue
        belastbar = bool(land["quality"].iloc[0] >= BELASTBAR)
        if nur_belastbar and not belastbar:
            continue
        farbe = FARBEN_LAENDER.get(iso2, ersatz[i % len(ersatz)])
        name = namen.get(iso2, iso2)
        gini = gini_aus_dezilen(land["anteil"])
        ginis.append((gini, name, farbe))
        n_belastbar += belastbar
        x = [0, *range(10, 101, 10)]
        y = [0, *(land["anteil"].cumsum() * 100)]
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="lines+markers", name=f"{name} (Gini {de(gini, 2)})",
            line={"color": farbe, "width": 2.5 if belastbar else 2,
                  "dash": "solid" if belastbar else "dash"},
            marker={"size": 6, "symbol": "circle" if belastbar else "circle-open"},
            opacity=1.0 if belastbar else 0.6,
            hovertemplate=f"{name}: ärmste %{{x}} % besitzen %{{y:.1f}} %<extra></extra>",
        ))  # fmt: skip
    if not ginis:
        raise ValueError(f"Keine vollständigen Dezildaten für {iso2s} in {jahr}")
    ginis.sort()
    # 1:1-Seitenverhältnis: Plotly verkleinert den Zeichenbereich (constrain=
    # "domain"), statt die Achsenspanne zu strecken
    fig.update_xaxes(
        title="Anteil der Bevölkerung, ärmste zuerst (%)", range=[0, 100], dtick=20,
        constrain="domain",
    )  # fmt: skip
    fig.update_yaxes(
        title="Kumulierter Vermögensanteil (%)", range=[-12, 100], dtick=20,
        scaleanchor="x", scaleratio=1, constrain="domain",
    )  # fmt: skip
    # Legende unter dem Plot (der quadratische Plot lässt seitlich Leerraum,
    # den eine seitliche Legende nur scheinbar füllt)
    fig.update_layout(
        legend={"orientation": "h", "x": 0.5, "xanchor": "center", "y": -0.14,
                "yanchor": "top"}
    )  # fmt: skip
    fig.add_annotation(
        x=50, y=-9, text="unter 0: Nettoschulden der ärmsten Dezile", showarrow=False,
        font={"color": GRAU, "size": SCHRIFTGROESSE - 2}, xanchor="left",
    )  # fmt: skip
    kennzeichnung = (
        " — alle Werte geschätzt" if n_belastbar == 0
        else f" — {len(ginis) - n_belastbar} von {len(ginis)} geschätzt" if n_belastbar < len(ginis)
        else ""
    )  # fmt: skip
    return basis_layout(
        fig,
        titel=f"{jahr}: Gini von {de(ginis[0][0], 2)} ({ginis[0][1]}) bis "
        f"{de(ginis[-1][0], 2)} ({ginis[-1][1]}){kennzeichnung}",
        untertitel="Lorenzkurven aus Dezilanteilen am Netto-Privatvermögen; "
        + HINWEIS_BELASTBAR,
        quelle=QUELLE_WID,
        fuss_abstand=175,
        rand_unten=200,
    )


# --- C7: Median vs. Mittelwert -------------------------------------------------
def median_mittel_dumbbell(
    lj: pd.DataFrame,
    iso2s: list[str],
    jahr: int = 2023,
    namen: dict[str, str] | None = None,
) -> go.Figure:
    """C7 — Wie schief ist die Vermögensverteilung?

    Median und Durchschnitt je Erwachsenem in Kaufkraftdollar (Preise 2025),
    nach Differenz sortiert. Alle Werte sind für 2023 imputiert und werden
    als geschätzt gekennzeichnet (hohle Marker, Untertitel).
    """
    namen = namen or {}
    d = (
        lj[lj["iso2"].isin(iso2s) & (lj["jahr"] == jahr)]
        .dropna(subset=["ahweal_ppp_usd", "median_weal_ppp_usd"])
        .copy()
    )
    d["name"] = d["iso2"].map(lambda i: namen.get(i, i))
    d["differenz"] = d["ahweal_ppp_usd"] - d["median_weal_ppp_usd"]
    d["faktor"] = d["ahweal_ppp_usd"] / d["median_weal_ppp_usd"]
    d = d.sort_values("differenz")  # größte Differenz oben

    fig = go.Figure()
    for _, z in d.iterrows():
        fig.add_trace(go.Scatter(
            x=[z["median_weal_ppp_usd"], z["ahweal_ppp_usd"]], y=[z["name"], z["name"]],
            mode="lines", line={"color": GRAU_HELL, "width": 3}, showlegend=False,
            hoverinfo="skip",
        ))  # fmt: skip
    fig.add_trace(go.Scatter(
        x=d["median_weal_ppp_usd"], y=d["name"], mode="markers", name="Median",
        marker={"size": 14, "color": "white", "symbol": "circle",
                "line": {"color": OKABE_ITO["blau"], "width": 2.5}},
        hovertemplate="%{y} Median: %{x:,.0f} $<extra></extra>",
    ))  # fmt: skip
    fig.add_trace(go.Scatter(
        x=d["ahweal_ppp_usd"], y=d["name"], mode="markers", name="Durchschnitt",
        marker={"size": 14, "color": "white", "symbol": "diamond",
                "line": {"color": OKABE_ITO["rotorange"], "width": 2.5}},
        hovertemplate="%{y} Durchschnitt: %{x:,.0f} $<extra></extra>",
    ))  # fmt: skip
    # Faktor als direkte Beschriftung rechts vom Durchschnitt
    for _, z in d.iterrows():
        fig.add_annotation(
            x=z["ahweal_ppp_usd"], y=z["name"], text=f"× {de(z['faktor'], 1)}",
            xanchor="left", xshift=12, showarrow=False,
            font={"size": SCHRIFTGROESSE - 1, "color": GRAU},
        )  # fmt: skip
    schiefstes = d.iloc[-1]
    fig.update_xaxes(
        title="Vermögen je Erwachsenem in Kaufkraftdollar (Preise 2025)",
        range=[0, d["ahweal_ppp_usd"].max() * 1.15], tickformat=",.0f", showgrid=True,
        gridcolor=GRAU_HELL,
    )  # fmt: skip
    fig.update_yaxes(title=None, showgrid=False)
    fig.update_layout(
        legend={
            "orientation": "h",
            "x": 1,
            "xanchor": "right",
            "y": 1.02,
            "yanchor": "bottom",
        }
    )
    return basis_layout(
        fig,
        titel=f"In den {schiefstes['name']} ist der Durchschnitt das "
        f"{de(schiefstes['faktor'], 1)}-Fache des Medians"
        if schiefstes["iso2"] == "US"
        else f"{schiefstes['name']}: Durchschnitt ist das {de(schiefstes['faktor'], 1)}-Fache "
        "des Medians",
        untertitel=f"Netto-Privatvermögen je Erwachsenem {jahr}, sortiert nach Differenz — "
        "alle Werte geschätzt, letzte Messung 2022",
        quelle=QUELLE_WID + "; PPP-Umrechnung mit Rate des Preisbasisjahres 2025",
    )


# --- C8: Zusammenhang Medianalter × Top 10 % -----------------------------------
def scatter_alter_vermoegen(
    lj: pd.DataFrame,
    jahr: int,
    hervorheben: dict[str, str] | None = None,
    nur_belastbar: bool = False,
) -> go.Figure:
    """C8 — Konzentriert sich Vermögen in alten Gesellschaften?

    Streudiagramm Medianalter × Anteil der reichsten 10 %, Fläche ∝
    Bevölkerung, Farbe = Region (Okabe-Ito), Markerform = Qualität
    (gefüllt = belastbar, hohl = geschätzt). Keine Regressionslinie —
    Ländermittelwerte sagen nichts über Individuen (ökologischer Fehlschluss).
    """
    hervorheben = hervorheben or {}
    d = (
        lj[(lj["jahr"] == jahr)]
        .dropna(subset=["top10", "medianalter", "region"])
        .copy()
    )
    d["belastbar"] = d["quality_top10"] >= BELASTBAR
    if nur_belastbar:
        d = d[d["belastbar"]]
    d["top10_pct"] = d["top10"] * 100
    d["bev_mio"] = d["bevoelkerung_tsd"] / 1000
    n_belastbar = int(d["belastbar"].sum())

    fig = go.Figure()
    # Fläche ∝ Bevölkerung: sizemode="area" mit sizeref aus dem Maximum
    sizeref = 2.0 * d["bev_mio"].max() / (45.0**2)
    for region, farbe in FARBEN_REGION.items():
        for belastbar, symbol in [(True, "circle"), (False, "circle-open")]:
            teil = d[(d["region"] == region) & (d["belastbar"] == belastbar)]
            if teil.empty:
                continue
            fig.add_trace(go.Scatter(
                x=teil["medianalter"], y=teil["top10_pct"], mode="markers",
                name=region, legendgroup=region, showlegend=belastbar or
                d[(d["region"] == region) & d["belastbar"]].empty,
                marker={"size": teil["bev_mio"], "sizemode": "area", "sizeref": sizeref,
                        "sizemin": 4, "color": farbe, "symbol": symbol,
                        "line": {"width": 1.5, "color": farbe}, "opacity": 0.75},
                customdata=teil[["land", "bev_mio", "quality_top10"]],
                hovertemplate="%{customdata[0]}<br>Medianalter %{x:.1f} Jahre · "
                              "Top 10 %: %{y:.1f} %<br>%{customdata[1]:,.1f} Mio. Einw. · "
                              "Qualität %{customdata[2]:.0f}<extra></extra>",
            ))  # fmt: skip
    # Legende für die Markerform (Dummy-Spuren ohne Daten)
    for symbol, text in [
        ("circle", f"belastbar (Qualität ≥ {BELASTBAR})"),
        ("circle-open", "geschätzt"),
    ]:
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="markers", name=text,
            marker={"size": 10, "color": GRAU, "symbol": symbol,
                    "line": {"width": 1.5, "color": GRAU}},
        ))  # fmt: skip
    for iso2, name in hervorheben.items():
        z = d[d["iso2"] == iso2]
        if z.empty:
            continue
        fig.add_annotation(
            x=z["medianalter"].iloc[0], y=z["top10_pct"].iloc[0], text=name,
            showarrow=True, arrowhead=0, arrowcolor=GRAU, ax=0, ay=-22,
            font={"size": SCHRIFTGROESSE - 1},
        )  # fmt: skip
    fig.update_xaxes(title="Medianalter (Jahre)", showgrid=True, gridcolor=GRAU_HELL)
    fig.update_yaxes(title="Vermögensanteil der reichsten 10 % (%)")
    fig.update_layout(
        legend={
            "x": 1.0,
            "y": 1.0,
            "xanchor": "right",
            "yanchor": "top",
            "bgcolor": "rgba(255,255,255,0.85)",
        }
    )
    korr = d[["medianalter", "top10_pct"]].corr().iloc[0, 1]
    return basis_layout(
        fig,
        titel=f"{jahr}: Alter erklärt Vermögenskonzentration kaum "
        f"(Korrelation {de(korr, 2)}, {len(d)} Länder, {n_belastbar} belastbar)",
        untertitel="Fläche ∝ Bevölkerung; Ländermittelwerte, keine Aussage über Personen "
        "(ökologischer Fehlschluss); Medianalter 1. Juli",
        quelle=f"{QUELLE_WPP}; {QUELLE_WID}",
    )


# --- C9: Datenqualität nach Region ----------------------------------------------
def qualitaet_nach_region(q: pd.DataFrame) -> go.Figure:
    """C9 — Wie viel der Vermögensdaten ist gemessen?

    Je Region: Länder nach höchster je erreichter Qualitätsstufe (1975–2024),
    gestapelt; Stufe 0 als Basis ist direkt ablesbar. Länder ohne Reihe grau.
    """
    d = q.copy()
    d["stufe"] = d["max_quality"].where(d["hat_daten"], -1).astype(int)
    tab = d.groupby(["region", "stufe"]).size().unstack(fill_value=0)
    for s in range(-1, 6):
        if s not in tab.columns:
            tab[s] = 0
    tab = tab[[*range(6), -1]]
    tab = tab.loc[tab.sum(axis=1).sort_values().index]  # größte Region oben

    fig = go.Figure()
    for stufe in tab.columns:
        werte = tab[stufe]
        if stufe == -1:
            name, farbe = "keine Vermögensreihe", FARBE_KEINE_DATEN
        else:
            name, farbe = f"Qualität {stufe}", FARBEN_QUALITAET[stufe]
        fig.add_trace(go.Bar(
            y=tab.index, x=werte, orientation="h", name=name, marker_color=farbe,
            marker_line={"color": "white", "width": 1},
            text=[str(v) if v >= 3 else "" for v in werte], textposition="inside",
            insidetextanchor="middle", textfont={"color": "white" if stufe not in (-1, 0, 1)
                                                  else "#222", "size": SCHRIFTGROESSE - 1},
            hovertemplate=f"%{{y}} · {name}: %{{x}} Länder<extra></extra>",
        ))  # fmt: skip
    gesamt = tab.sum(axis=1)
    for region, summe in gesamt.items():
        belastbar = int(tab.loc[region, [3, 4, 5]].sum())
        fig.add_annotation(
            x=summe, y=region, text=f"{belastbar} von {int(tab.loc[region, list(range(6))].sum())} "
            "je belastbar", xanchor="left", xshift=8, showarrow=False,
            font={"size": SCHRIFTGROESSE - 1, "color": GRAU},
        )  # fmt: skip
    n_mit = int(d["hat_daten"].sum())
    n_bel = int((d["max_quality"] >= BELASTBAR).sum())
    fig.update_layout(
        barmode="stack", legend={"orientation": "h", "x": 0, "y": 1.02, "yanchor": "bottom",
                                 "traceorder": "normal"},
    )  # fmt: skip
    fig.update_xaxes(title="Anzahl Länder", range=[0, gesamt.max() * 1.35])
    fig.update_yaxes(title=None)
    return basis_layout(
        fig,
        titel=f"Nur {n_bel} von {n_mit} Ländern mit Vermögensdaten waren je belastbar gemessen",
        untertitel="Höchste erreichte WID-Qualitätsstufe der Top-10-%-Reihe 1975–2024, "
        f"belastbar = Stufe ≥ {BELASTBAR}; Stufe 0 = reine Schätzung/Imputation",
        quelle=QUELLE_WID,
    )


# --- C10: Der Bruch ----------------------------------------------------------------
def bruch_frankreich(
    lj: pd.DataFrame, iso2: str = "FR", name: str = "Frankreich"
) -> go.Figure:
    """C10 — Was verbirgt eine durchgezogene Linie?

    Dieselbe Reihe (Top 10 % Frankreich 1975–2024) zweimal nebeneinander:
    links ohne, rechts mit Qualitätskennzeichnung. Rechts wird sichtbar,
    dass die Reihe ab 2015 auf Qualität 0 fällt.
    """
    land = lj[(lj["iso2"] == iso2)].dropna(subset=["top10"]).sort_values("jahr").copy()
    land["top10_pct"] = land["top10"] * 100
    farbe = FARBEN_LAENDER.get(iso2, OKABE_ITO["blau"])
    fig = make_subplots(
        rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.06,
        subplot_titles=["<b>So sieht es meist aus</b>", "<b>So sieht es wirklich aus</b>"],
    )  # fmt: skip
    fig.add_trace(go.Scatter(
        x=land["jahr"], y=land["top10_pct"], mode="lines", name=name, showlegend=False,
        line={"color": farbe, "width": 2.5},
        hovertemplate=f"{name} %{{x}}: %{{y:.1f}} %<extra></extra>",
    ), row=1, col=1)  # fmt: skip
    _linie_mit_qualitaet(fig, land, name, farbe, "top10_pct", ".1f", row=1, col=2)

    # Bruchstelle: erstes Jahr ohne belastbare Qualität nach dem letzten belastbaren
    belastbar = land[land["quality_top10"] >= BELASTBAR]
    if not belastbar.empty:
        letztes = int(belastbar["jahr"].max())
        danach = land[land["jahr"] > letztes]
        if not danach.empty:
            fig.add_vline(
                x=letztes + 0.5,
                line={"color": GRAU, "width": 1, "dash": "dot"},
                row=1,
                col=2,
            )
            fig.add_annotation(
                x=land["jahr"].max(), y=land["top10_pct"].min() * 0.93, xref="x2", yref="y2",
                text=f"ab {letztes + 1}: Qualität {int(danach['quality_top10'].iloc[0])} "
                "(Imputation)", xanchor="right", yanchor="bottom", showarrow=False,
                font={"color": GRAU, "size": SCHRIFTGROESSE - 1},
            )  # fmt: skip
            fig.add_annotation(
                x=letztes - 1, y=land["top10_pct"].max() * 1.05, xref="x2", yref="y2",
                text=f"bis {letztes}: Qualität {int(belastbar['quality_top10'].iloc[-1])} "
                "(Steuerdaten)", xanchor="right", yanchor="top", showarrow=False,
                font={"color": GRAU, "size": SCHRIFTGROESSE - 1},
            )  # fmt: skip
    y_min = land["top10_pct"].min() * 0.9
    y_max = land["top10_pct"].max() * 1.1
    fig.update_yaxes(range=[y_min, y_max])
    fig.update_yaxes(title="Vermögensanteil der reichsten 10 % (%)", row=1, col=1)
    fig.update_xaxes(
        title="Jahr", dtick=10, range=[land["jahr"].min(), land["jahr"].max()]
    )
    fig.update_annotations(yshift=6, selector={"xref": "paper"})
    fig = basis_layout(
        fig,
        titel=f"{name}: Dieselbe Linie — gemessen bis {letztes}, danach geschätzt",
        untertitel=f"Anteil der reichsten 10 % am Netto-Privatvermögen {int(land['jahr'].min())}–"
        f"{int(land['jahr'].max())}; rechts: {HINWEIS_BELASTBAR}",
        quelle=QUELLE_WID,
    )
    fig.update_layout(margin={"t": 140})
    return fig
