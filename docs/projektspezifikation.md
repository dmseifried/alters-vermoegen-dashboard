# Projektspezifikation: Alters- und Vermögensverteilungen international

Diese Datei beschreibt Fragestellung, Datengrundlage, Definitionen und
methodische Entscheidungen des Projekts. Gestaltungsregeln für Charts stehen
separat in `docs/visualisierungsregeln.md`.

---

## 1. Kontext

Prüfungsleistung im Bachelor-Wahlmodul „Datenvisualisierung, Infografik und
Data Storytelling". Abgabe:

- ein **selbst gebautes, interaktives Dashboard** (Streamlit + Plotly)
- eine **Präsentation, 10–12 Folien, als PDF**, 15 Minuten Vortrag

Dieses Repository enthält das Dashboard und die exportierten Grafiken für die
Präsentation. Die Präsentation selbst ist nicht Teil des Repositorys.

---

## 2. Leitfrage und Story

> **Wie verteilen sich Alter und Vermögen international — und was wissen wir
> davon wirklich?**

Kernbefund: Die beiden Hälften des Themas sind sehr unterschiedlich
belastbar.

- **Alter** ist global gemessen (UN, alle Länder, harmonisiert).
- **Vermögen** ist global überwiegend *geschätzt*. WID liefert für 215 von 241
  Ländern lückenlose Reihen bis 2024 — der beobachtungsweise Qualitätsscore
  zeigt aber, dass fast alles auf Stufe 0 liegt. Selbst Frankreich, mit einer
  der besten Vermögensdatenlagen weltweit, fällt ab 2015 von Qualität 4 auf 0.
  Japan, Brasilien, Niger und Somalia liegen durchgehend bei 0.

Das Dashboard zeigt deshalb nicht nur Verteilungen, sondern macht die
**Belastbarkeit der Daten sichtbar**. Eine Visualisierung, die geschätzte und
gemessene Werte gleich aussehen lässt, gilt in diesem Projekt als Fehler.

Dramaturgie (entspricht den Dashboard-Bereichen):

1. Die Welt altert — sehr ungleich
2. Vermögen ist ungleicher verteilt als Alter
3. Der Zusammenhang zwischen beidem
4. Die Wendung: Wie viel davon ist gemessen?

---

## 3. Datenquellen

Die Rohdaten liegen in `data/raw/` und sind nicht Teil des Repositorys. Sie
werden nur gelesen, nie verändert.

### 3.1 UN World Population Prospects 2024 — `data/raw/wpp/`

| Datei | Inhalt |
|---|---|
| `WPP2024_Demographic_Indicators_Medium.csv.gz` | Kennzahlen pro Land und Jahr, 1950–2100 |
| `WPP2024_Population1JanuaryByAge5GroupSex_Medium.csv.gz` | Bevölkerung nach Fünfjahresgruppen und Geschlecht, Stichtag 1. Januar |
| `WPP2024_Locations_notes.csv` | Metadaten zu Orten |
| `WPP2024_Demographic_Indicators_notes.csv` | Metadaten zu Indikatoren |

Eigenheiten:

- Trennzeichen Komma, Dateien beginnen mit einem BOM (`utf-8-sig`).
- Enthält neben Ländern auch Aggregate (Welt, Kontinente,
  Einkommensgruppen). Filter: `LocTypeName == "Country/Area"`.
- Verwendete Spalten der Indikatorendatei: `ISO2_code`, `ISO3_code`,
  `Location`, `LocTypeName`, `ParentID`, `Time`, `TPopulation1July`,
  `MedianAgePop`, `TFR`, `LEx`, `LE65`. Der Altersgruppen-Datei: `AgeGrp`,
  `AgeGrpStart`, `PopMale`, `PopFemale`, `PopTotal`.
- **Bevölkerungszahlen in Tausend**, in Spaltennamen mit `_tsd` kenntlich.
- **Namibia hat den ISO2-Code `NA`**, den pandas standardmäßig als fehlenden
  Wert liest. Eingelesen wird daher mit `keep_default_na=False`, abgesichert
  per Test.
- Der Altenquotient (OADR) ist nicht als Indikator enthalten und wird aus der
  Altersgruppen-Datei berechnet: Bevölkerung 65+ / 15–64.
- Stichtage: Indikatoren meist 1. Juli, Altersgruppen 1. Januar.
- Werte ab 2024 sind Projektionen (Medium-Variante) und in Charts von
  Beobachtungen unterschieden.

### 3.2 World Inequality Database — `data/raw/wid/`

Bulk-Download, 423 Länder- und Regionsdateien, Abruf 9.9.2026 (Konstante
`QUELLE_WID` in `src/load.py`).

| Datei | Inhalt |
|---|---|
| `WID_countries.csv` | Codes, Namen, Weltregionen |
| `WID_data_XX.csv` | Daten pro Land/Region XX |
| `WID_metadata_XX.csv` | Methodik und Quellen pro Variable |
| `README.md` | Formatbeschreibung |

Eigenheiten:

- **Trennzeichen Semikolon.** Spalten:
  `country;variable;percentile;year;value;age;pop;data_quality`
- **Variablencodes sind anders aufgebaut als im WID-README beschrieben:**
  Typ + Konzept + Bevölkerungseinheit + Altersgruppe, also `shwealj992`,
  nicht `shweal992j`.
- Verwendete Variablen:

  | Code | Bedeutung |
  |---|---|
  | `shwealj992` | Anteil am Netto-Privatvermögen, equal-split adults, 20+ (Kernvariable) |
  | `ahwealj992` | Durchschnittsvermögen |
  | `thwealj992` | Schwellenwerte (für den Median) |
  | `xlcuspi999` | Kaufkraftparität lokale Währung je US-Dollar |
  | `inyixxi999` | Preisindex Nationaleinkommen |

  `shwealj999` (alle Altersgruppen) ist eine andere Reihe und wird bewusst
  nicht geladen; deshalb werden exakte Codes statt eines Präfixfilters
  verwendet.
- Anteile sind **Brüche von 1** (0,2 = 20 %).
- Verwendete Perzentilgruppen: `p0p50`, `p50p90`, `p90p100`, `p99p100`, für
  Lorenzkurven die Dezile `p0p10` … `p90p100`.
- Echte Länder: `alpha2` mit genau zwei Zeichen. Codes mit Bindestrich sind
  Subregionen oder Wechselkursvarianten (`-MER`).
- **`data_quality`: Skala 0–5**, 0 = niedrigste gültige Stufe (Schätzung bzw.
  Imputation), NaN = kein Score. Variiert nach Land, Reihe und Jahr. Stufe 5
  erreichen Dänemark, Island, Norwegen und Schweden.
- Die Reihen sind rasterartig aufgefüllt (identische Beobachtungszahlen über
  Länder hinweg, Reihen ab 1820 auch für Staaten, die es damals nicht gab).
  Die Metadaten-Spalte `source` belegt: Viele Länder haben als einzige Quelle
  das Imputationspapier (Bajard et al. 2021/2025, *Global Wealth Inequality
  on WID.world: Estimates and Imputations*).
- Das Einlesen aller Dateien ist langsam. Die benötigten Variablen und
  Perzentile werden einmal vorverarbeitet und als Parquet in
  `data/processed/` gespeichert.

### 3.3 Join

- WID `alpha2` ↔ WPP `ISO2_code`, ohne externes Mapping-Paket.
- **WPP ist die Basis, WID wird per `how="left"` angehängt.** Länder ohne
  Vermögensdaten bleiben erhalten, damit die Datenlücke darstellbar ist.
- Jeder Merge mit `indicator=True` und `validate=`; nicht gematchte Codes
  werden ausgegeben und in `join_protokoll.csv` protokolliert.

### 3.4 Nicht verwendet

UBS Global Wealth Report und OECD Wealth Distribution Database werden nicht
eingelesen. OECD ist als mögliche Erweiterung vorgemerkt (Abschnitt 11).

---

## 4. Definitionen

| Begriff | Definition |
|---|---|
| **Belastbar** | `data_quality >= 3` (Konstante `BELASTBAR` in `src/load.py`) |
| **Vertiefungsländer** | Frankreich, USA, Deutschland, Indien, China, Japan, Niger, Südafrika (Konstante `VERTIEFUNGSLAENDER` in `src/load.py`) |
| **Beobachtungszeitraum** | 1990–2023 (WPP-Schätzungen) |
| **Projektionszeitraum** | 2024–2050 (WPP Medium) |
| **Vermögensanteil Top 10 %** | `shwealj992`, `p90p100` |
| **Median-Vermögen** | Schwelle der oberen Hälfte aus `thwealj992`, Perzentil `p50p100` (`thwealj992` hat kein `p50`; `p50p51` liefert denselben Wert) |

Die Vertiefungsländer wurden nach der Qualitätsauswertung über alle
WID-Länder gewählt: Länder mit belastbaren Reihen, ergänzt um Kontrastländer
mit sehr junger bzw. sehr alter Bevölkerung. Die Spannweite Niger–Japan deckt
die Demografie ab, Japan–USA die Datenqualität.

---

## 5. Datenmodell (`data/processed/`)

| Datei | Ebene | Inhalt |
|---|---|---|
| `laender_jahr.parquet` | Land × Jahr | iso2, iso3, land, region, jahr, bevoelkerung_tsd, medianalter, fertilitaet, lebenserwartung, lebenserwartung_65, oadr, top10, top1, bottom50, mittel50_90, ahweal, median_weal, quality_top10 |
| `pyramide.parquet` | Land × Jahr × Altersgruppe × Geschlecht | iso3, jahr, altersgruppe, geschlecht, bevoelkerung_tsd, anteil |
| `wid_dezile.parquet` | Land × Jahr × Dezil | für Lorenzkurven, inkl. Qualität |
| `wid_qualitaet.parquet` | Land | max_quality, anteil_quality_0, letztes_belastbares_jahr, quellen (aus Metadaten) |
| `join_protokoll.csv` | Code | nicht gematchte Codes beider Seiten |

---

## 6. Charts

Jeder Chart ist eine Funktion in `src/charts.py` und gibt ein `go.Figure`
zurück.

| # | Chart | Frage | Umsetzung |
|---|---|---|---|
| C1 | Bevölkerungspyramide | Wie ist die Altersstruktur? | Divergierende Balken, relative Anteile, x-Achse beidseitig positiv beschriftet; Land und Jahr wählbar |
| C2 | Pyramiden-Vergleich | Wie unterschiedlich altern Länder? | Small Multiples, 4 Länder, gemeinsame Skala |
| C3 | Medianalter-Karte | Wo ist die Welt alt, wo jung? | Choropleth, Equal-Earth-Projektion, sequenzielle Skala (viridis) |
| C4 | OADR 1990–2050 | Wie entwickelt sich die Last? | Linien, Projektion ab 2024 gestrichelt mit vertikaler Trennlinie |
| C5 | Vermögensanteile im Zeitverlauf | Wie konzentriert ist Vermögen? | Top 10 % je Vertiefungsland; Abschnitte mit Qualität < 3 gestrichelt und aufgehellt |
| C6 | Lorenzkurven | Wie ungleich insgesamt? | aus Dezilanteilen, 1:1-Seitenverhältnis, Diagonale als Referenz, Gini als Annotation |
| C7 | Median vs. Mittelwert | Wie schief ist die Verteilung? | Dumbbell, nach Differenz sortiert; Jahr 2023, in Kaufkraftdollar (Preise 2025, nur hier); alle Werte als geschätzt gekennzeichnet |
| C8 | Zusammenhang | Konzentriert sich Vermögen in alten Gesellschaften? | Scatter Medianalter × Top 10 %, Größe = Bevölkerung (Fläche ∝ Wert), Farbe = Region (Okabe-Ito), Markerform nach Qualität, Jahr wählbar |
| C9 | Datenqualität | Wie viel ist gemessen? | Balken: Länder je höchster erreichter Qualitätsstufe, nach Region |
| C10 | Der Bruch | Was verbirgt eine durchgezogene Linie? | Frankreich Top 10 % 1975–2024 zweimal nebeneinander: einmal ohne, einmal mit Qualitätskennzeichnung |

C9 und C10 sind die zentralen Grafiken des Projekts.

Jeder Chart hat einen aussagekräftigen Titel (Aussage, nicht Inhalt), Achsen
mit Einheit, Quelle und Abrufdatum als Fußzeile und deutsche Zahlenformate.

---

## 7. Dashboard

`app.py`, Streamlit, vier Tabs entlang der Dramaturgie:

1. **Demografie** — C1, C2, C3, C4
2. **Vermögen** — C5, C6, C7
3. **Zusammenhang** — C8
4. **Datenqualität & Methodik** — C9, C10, Quellenliste, Limitationen
   (ökologischer Fehlschluss, Imputation, Stichtage, Projektionen)

Globale Sidebar: Länderauswahl, Jahr, Schalter **„nur belastbare Werte
(Qualität ≥ 3)"**, der in allen Vermögens-Charts wirkt.

Die App lädt nur aus `data/processed/` (mit `@st.cache_data`), nie
Rohdaten.

---

## 8. Export

`scripts/export_figures.py` exportiert C1–C10 statisch nach `figures/` als
PNG und SVG, 16:9, Schrift mindestens 14 pt, über `kaleido`. C8 wird
zusätzlich für 2017 exportiert, weil 2023 alle Vermögenswerte Qualität 0
haben.

---

## 9. Technik und Konventionen

- Python 3.12, Abhängigkeiten mit **uv**, Ausführung mit `uv run`.
- pandas 3.x, Plotly 7.x, Streamlit, kaleido; ruff für Formatierung.
- Flache Struktur: `src/load.py`, `src/clean.py`, `src/charts.py`,
  `src/abdeckung.py`, `app.py`, `scripts/`, `tests/`.
- Kommentare und Docstrings auf Deutsch; Funktionen statt Klassen.

---

## 10. Validierung

`clean.py` gibt nach jedem Aufbereitungsschritt aus:

- Zeilenzahl vorher/nachher bei jedem Filter und Merge
- Merge-Indikatoren (`_merge`-Verteilung)
- Anzahl Länder in WPP (≈ 237) und in WID (241 echte Länder)
- Summe der Gruppenanteile p0p50 + p50p90 + p90p100 ≈ 1 (Toleranz ± 0,005)
- Wertebereiche (Anteile, Medianalter 10–65)

Tests in `tests/` (pytest):

- Namibia ist nach dem Laden vorhanden und hat `iso2 == "NA"`
- keine Aggregate in `laender_jahr`
- Anteilssummen plausibel
- nur `shwealj992`, kein `shwealj999`
- Wertebereiche
- Dashboard läuft headless ohne Fehler (streamlit AppTest)

---

## 11. Abgrenzung

Bewusst nicht Teil des Projekts:

- Einkommensverteilung (WID hätte sie — eine zweite Geschichte)
- alternative UN-Szenarien
- kausale Aussagen und Regressionsmodelle über eine Trendlinie mit
  Unsicherheitsband hinaus
- Deployment, Docker
- Daten vor 1975 (Ausnahme C10) und nach 2050

Mögliche Erweiterungen:

- OECD Wealth Distribution Database als gemessener Kontrast (5–8 Länder)
- Unsicherheits-Chart mit WPP-Szenarien
- Transparenzindex von WID ergänzend zum beobachtungsweisen Score

---

## 12. Methodik

### 12.1 PPP-Umrechnung und ihre Verzerrungen

Durchschnitts- und Medianvermögen (`ahwealj992`, `thwealj992`) liegen in
lokaler Währung zu konstanten Preisen vor; das Preisbasisjahr ist das Jahr,
in dem der WID-Preisindex `inyixxi999` gleich 1 ist (Stand der Daten: 2025).
Für Ländervergleiche werden sie mit der Kaufkraftparität `xlcuspi999`
(WID, Quelle Weltbank, aus dem ICP 2021 über den relativen Preisindex
fortgeschrieben) in Kaufkraftdollar umgerechnet — mit **einer** Rate je
Land, der des Preisbasisjahres. `clean.py` bricht ab, wenn PPP-Jahr und
Preisbasisjahr auseinanderfallen. Jahresspezifische Raten wären ein
Einheitenfehler (laufende gegen konstante Preise; bei Brasilien, der
Türkei, Argentinien wegen Währungsreformen unbrauchbar).

Kaufkraftdollar werden **nur in C7** verwendet, für ein einzelnes Jahr
(2023). Alle Anteile (Top 10 %, Top 1 %, Bottom 50 %, Dezile, Lorenz) sind
einheitenfrei und davon unberührt.

Vier Verzerrungen, die bei langen Reihen entstehen:

1. **Ein Warenkorb für fünfzig Jahre.** Die PPP des Basisjahres bewertet
   Güter mit den relativen Preisen dieses Jahres. Je weiter ein Jahr
   entfernt liegt, desto weniger passt der Korb (Indexproblem; es gibt
   keine richtige Lösung, nur eine deklarierte Wahl).
2. **Preisniveaus wandern.** Aufholende Länder werden relativ teurer
   (Balassa-Samuelson-Effekt). Die Rate des Basisjahres bewertet Indiens
   Vermögen von 1975 mit dem Preisniveau eines reicheren Indiens. Innerhalb
   eines Landes bleibt der Verlauf korrekt, der Abstand zwischen Ländern
   ist in frühen Jahren unsicherer als in späten.
3. **Der falsche Deflator.** WID rechnet Vermögen mit dem Preisindex des
   Nationaleinkommens in konstante Preise, nicht mit Vermögenspreisen.
   Steigen Immobilien oder Aktien schneller als das allgemeine
   Preisniveau, erscheint das als reales Vermögenswachstum.
4. **PPP misst Konsum, nicht Vermögen.** Das ICP vergleicht Preise für
   Konsumgüter und Investitionen; Immobilienpreise zwischen Ländern sind
   damit schlecht abgebildet.

### 12.2 Datenbereinigung im Einzelnen

- **Negative Anteile.** `bottom50` kann negativ werden (bis −0,11; u. a.
  Südafrika, USA, Dänemark): Das Nettovermögen der unteren Hälfte kann durch
  Schulden unter null liegen. Die Plausibilitätsprüfung „Anteile 0–1" gilt
  dafür nicht; in Lorenzkurven beginnt die Kurve dann unterhalb der
  Nulllinie.
- **Kosovo-Zusammenführung.** WID führt Kosovo doppelt: `KS` (mit
  Vermögensreihe, kein ISO-Code) und `XK` (ohne Reihe, ISO-Code wie bei
  WPP). `clean.py` ersetzt `KS` durch `XK` und entfernt den Doppeleintrag.
  Damit hat WID 241 echte Länder, nicht 242.
- **ParentID-918-Mapping.** Bermuda, Kanada, Grönland, St. Pierre &
  Miquelon und die USA verweisen in WPP auf die ParentID 918, die in der
  Indikatorendatei nicht vorkommt. `clean.py` ordnet sie explizit
  „Americas" zu; Regionen sind sonst aus der WPP-Hierarchie abgeleitet
  (fünf Kontinente, identisch mit den WID-Weltregionen, auf Deutsch).
- **Regionen einheitlich aus der WPP-Hierarchie.** Auch `wid_qualitaet.parquet`
  nutzt die WPP-Region (UN-Geoschema), nicht die aus `WID_countries.csv`.
  Vier Länder sind dort anders eingeteilt: Zypern (WID: Europa, WPP: Asien),
  Belarus, Russland und Ukraine (WID: Asien, WPP: Europa). Die Regionssummen
  in C9 weichen dadurch von der WID-Einteilung ab: Zypern ist belastbar
  (Qualität 3, 2010–2017) und zählt nun zu Asien, also Europa 25 statt 26
  belastbare Länder, Asien 3 statt 2. Nur historische Staaten ohne
  WPP-Eintrag behalten die WID-Region.
- **Medianalter über 60.** Der Heilige Stuhl (ab 2009) und Hongkong
  (Projektion ab 2047) liegen bei 62; Prüfbereich und Test nutzen 10–65.
