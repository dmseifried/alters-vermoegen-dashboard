# Visualisierungsregeln

Verbindliche Gestaltungsregeln für dieses Projekt.
Grundlage: Claus O. Wilke, *Fundamentals of Data Visualization* (O'Reilly 2019),
ergänzt um Cleveland & McGill (1984) und Cairo, *How Charts Lie* (2019).

Diese Datei ist die Referenz für alle Charts in `src/charts.py` und für den
Methodikteil der Präsentation.

---

## 0. Grundhaltung

- **Jede Grafik beantwortet genau eine Frage.** Erst die Frage formulieren, dann
  plotten. Nicht plotten und hinterher schauen, was man sieht.
- **Wilkes Dreiteilung:** Eine Grafik kann *hässlich* (ästhetische Mängel, aber
  korrekt), *schlecht* (unklar, verwirrend, unnötig kompliziert) oder *falsch*
  (objektiv fehlerhaft, irreführend) sein. Falsch ist nie akzeptabel,
  schlecht selten, hässlich manchmal tolerierbar unter Zeitdruck.
- **Eine Grafik zeigt nur, was sie zeigt.** Keine Aussage über Kausalität,
  Individuen oder Zeiträume, die nicht in den Daten stecken.
- **Selbsterklärend sein.** Wer die Grafik ohne Fließtext sieht, muss sie
  verstehen können.

---

## 1. Aesthetics — Daten auf visuelle Eigenschaften abbilden

Verfügbare Aesthetics: Position (x, y), Farbe, Form, Größe, Linienbreite,
Linientyp, Transparenz.

**Wahrnehmungsgenauigkeit, absteigend** (Cleveland & McGill 1984):

| Rang | Kodierung | Einsatz |
|---|---|---|
| 1 | Position auf gemeinsamer Skala | wichtigste Variable |
| 2 | Position auf getrennten Skalen | Small Multiples |
| 3 | Länge | Balken |
| 4 | Winkel / Steigung | Slope-Charts |
| 5 | Fläche | Bubble-Charts, sparsam |
| 6 | Volumen, Krümmung | vermeiden |
| 7 | Farbsättigung, Schattierung | nur ergänzend |

**Regel:** Die wichtigste Variable bekommt Position. Was man genau ablesen
können muss, wird nie über Fläche oder Farbe kodiert.

**Datentypen und passende Aesthetics:**

- *Quantitativ / kontinuierlich* → Position, Größe, Farbverlauf
- *Quantitativ / diskret* → Position, Größe
- *Qualitativ / ungeordnet* → Farbe (kategorial), Form
- *Qualitativ / geordnet* → Position, Farbverlauf, Sättigung

---

## 2. Koordinatensysteme und Achsen

- **Lineare Skalen als Standard.** Gleiche Abstände bedeuten gleiche Differenzen.
- **Logarithmische Skalen** nur bei multiplikativen Verhältnissen oder Spannweiten
  über mehrere Größenordnungen. Dann **immer explizit beschriften**
  („log₁₀-Skala") und Achsenticks an runden Zehnerpotenzen.
- **Aspect Ratio:** Das Seitenverhältnis beeinflusst die wahrgenommene Steigung.
  Bei Zeitreihen so wählen, dass typische Steigungen nahe 45° liegen
  (Banking to 45°).
- **Keine doppelten Y-Achsen.** Sie erzeugen beliebige Scheinkorrelationen,
  weil die relative Skalierung frei wählbar ist. Stattdessen: zwei Panels
  untereinander mit gemeinsamer X-Achse, oder Indexierung auf einen Basiswert.
- **Kein 3D** für 2D-Daten. Perspektive verzerrt Längen und Flächen systematisch.
  Echte 3D-Daten besser als Small Multiples oder Heatmap darstellen.
- **Achsenbereich:**
  - Balken: **zwingend bei Null beginnen** (Länge kodiert den Wert)
  - Punkte und Linien: Null nicht zwingend, Ausschnitt aber kennzeichnen
  - Nie den Ausschnitt so wählen, dass ein Effekt dramatischer wirkt

---

## 3. Farbe

Farbe hat **genau drei mögliche Funktionen**. Nie zwei gleichzeitig in einer Grafik.

### 3.1 Unterscheidung (qualitativ)

- Maximal **8 Kategorien**, besser 5. Darüber hinaus: gruppieren oder facettieren.
- Paletten: **Okabe-Ito** (farbfehlsichtigkeitssicher, 8 Farben),
  ColorBrewer `Set2`/`Dark2`, Plotly `Safe`
- Keine Regenbogenfolge für Kategorien

### 3.2 Repräsentation von Werten (sequenziell / divergierend)

**Sequenziell** (ein Extrem wichtig): `viridis`, `magma`, `cividis`.
Perzeptuell uniform und farbfehlsichtigkeitssicher.

**Divergierend** (Mitte ist neutral, beide Extreme wichtig): ColorBrewer `RdBu`,
`BrBG`, `PuOr`. **Mittelpunkt explizit setzen**, sonst verschiebt ihn die
Datenverteilung und die Grafik lügt.

**Nie `rainbow` oder `jet`.** Nicht perzeptuell uniform — erzeugt Artefakte,
die es in den Daten nicht gibt, und ist bei Farbfehlsichtigkeit unlesbar.

### 3.3 Hervorhebung

Eine Farbe für das Hervorgehobene, neutrales Grau für den Rest.
Das ist die wirksamste Technik für erzählende Grafiken.

### 3.4 Farbfehlsichtigkeit

Rund 8 % der Männer sind rot-grün-schwach. **Farbe nie als alleiniger Träger
einer Information.** Immer redundant kodieren: zusätzlich Form, Linientyp,
direkte Beschriftung oder Position.

Prüfen mit einem Simulator (z. B. Coblis) oder testweise in Graustufen
exportieren — wenn es dort unlesbar wird, ist es auch farbig fragil.

---

## 4. Mengen darstellen

**Balkendiagramme**
- Immer bei Null beginnen
- **Nach Wert sortieren**, nicht alphabetisch — außer die Kategorie hat
  eine eigene natürliche Ordnung (Jahre, Altersgruppen)
- Lange Kategorienamen: horizontale Balken
- Gruppierte Balken nur bis ~3 Untergruppen, sonst Small Multiples

**Punktdiagramme (Dot Plots)**
- Bessere Alternative zu Balken, wenn die Null nicht sinnvoll ist
- Weniger Tinte, gleiche Ablesegenauigkeit

**Dumbbell-Charts**
- Zwei Punkte pro Kategorie, verbunden
- Ideal für Vorher/Nachher oder Median vs. Mittelwert

**Heatmaps**
- Bei vielen Kategorien × vielen Zeitpunkten
- Zeilen und Spalten sinnvoll sortieren (nicht alphabetisch)
- Farbskala sequenziell, Legende zwingend

---

## 5. Verteilungen darstellen

**Histogramme**
- Die **Bin-Breite ist eine Entscheidung, keine Einstellung.** Mehrere
  ausprobieren, die gewählte begründen können
- Zu schmal: Rauschen; zu breit: Struktur verschwindet

**Dichteplots (KDE)**
- Bandbreite hat dasselbe Problem wie die Bin-Breite
- **Randprobleme beachten:** Bei begrenzten Größen (Alter ≥ 0, Anteile in
  [0,1]) läuft die Dichte über den Rand hinaus und suggeriert unmögliche Werte
- Bei kleinen Stichproben (n < 30) nicht verwenden

**ECDF (empirische Verteilungsfunktion)**
- Parameterfrei, keine willkürlichen Entscheidungen
- Zeigt alle Datenpunkte, ideal zum Vergleich mehrerer Verteilungen
- Unterschätzt, sollte häufiger eingesetzt werden

**Boxplots**
- Kompakt, gut für viele Gruppen
- **Verbergen Multimodalität** — zwei völlig verschiedene Verteilungen können
  identische Boxplots haben
- Bei n < 10 lieber alle Punkte zeigen

**Violin- und Sina-Plots**
- Zeigen die Verteilungsform, anders als Boxplots
- Sina-Plot (Punkte + Dichte) ist oft die ehrlichste Variante

**Ridgeline-Plots**
- Mehrere Verteilungen übereinander, leicht versetzt
- Stark für zeitliche Entwicklung von Verteilungen

---

## 6. Anteile darstellen

**Tortendiagramme**
- Vertretbar bei **2–3 Kategorien** und wenn es um „Teil vom Ganzen" geht
- Ab 4 Kategorien: gestapelte Balken oder Einzelbalken
- Nie mehrere Tortendiagramme zum Vergleich — Winkel vergleichen sich schlecht

**Gestapelte Balken**
- Nur die unterste Kategorie hat eine gemeinsame Basislinie und ist gut ablesbar
- Für Vergleiche über Gruppen ungeeignet

**Mosaikplots und Treemaps**
- Für verschachtelte Anteile über mehrere Dimensionen
- Flächenvergleich ist ungenau — nur für Übersicht, nicht für Präzision

**Parallele Sets**
- Für Flüsse zwischen Kategorien

---

## 7. Zusammenhänge zwischen zwei Variablen

**Streudiagramme**
- Standard für zwei kontinuierliche Variablen
- **Overplotting behandeln** (siehe 11)
- Regressionslinie nur mit Unsicherheitsband und nur, wenn ein linearer
  Zusammenhang plausibel ist

**Bubble-Charts**
- Dritte Variable über Punktgröße
- **Fläche ∝ Wert, nicht Radius** — sonst quadratische Verzerrung
- Größenlegende mit mindestens 3 Referenzgrößen
- Maximal eine zusätzliche Dimension, sonst unlesbar

**Slope-Charts**
- Zwei Zeitpunkte, viele Einheiten
- Steigung ist direkt ablesbar, Rangwechsel sichtbar

**Korrelogramme**
- Bei vielen Variablenpaaren
- Divergierende Farbskala, Mittelpunkt bei 0

---

## 8. Zeitreihen und Trends

- **Linien** für kontinuierliche Zeit, **Punkte** für diskrete Messzeitpunkte
- Lücken in den Daten als Lücken zeigen, nicht durchverbinden
- **Glättung** (LOESS, gleitender Mittelwert) nur mit sichtbaren Rohdaten
  im Hintergrund und Angabe der Methode
- **Keine Extrapolation über den Datenbereich hinaus**
- Bei Projektionen: klar von beobachteten Daten trennen — gestrichelte Linie,
  vertikale Trennlinie, Beschriftung

---

## 9. Unsicherheit

Wilke widmet der Unsicherheit ein eigenes Kapitel — sie ist der am häufigsten
weggelassene Teil einer Grafik.

- Fehlerbalken **immer beschriften**: Standardfehler? Standardabweichung?
  95-%-Konfidenzintervall? Ohne Angabe ist der Balken bedeutungslos
- Konfidenzbänder bei Linien statt Fehlerbalken
- **Frequency Framing** ist verständlicher als Wahrscheinlichkeiten:
  „12 von 100" statt „12 %"
- Quantile-Dotplots zeigen Unsicherheit intuitiv
- Wo Daten fehlen oder geschätzt sind: kennzeichnen, nicht glätten

---

## 10. Geodaten

- **Projektion ist eine Entscheidung.** Mercator verzerrt Flächen massiv
  (Grönland ≈ Afrika). Für Weltkarten besser: Equal Earth, Robinson,
  Winkel Tripel
- **Choroplethen zeigen Fläche, nicht Bevölkerung.** Große dünn besiedelte
  Länder dominieren optisch. Für Bevölkerungsbezug: Kartogramm oder
  Kachel-Karte
- Karten sind gut für geografische Orientierung, **schlecht für
  Größenvergleiche**. Wenn es um Werte geht: sortierter Balken statt Karte
- Verwendete Projektion in der Bildunterschrift nennen

---

## 11. Overplotting

Wenn Punkte einander überdecken:

1. **Transparenz** (`alpha` 0.1–0.5) — erste Wahl bei mittlerer Dichte
2. **Jitter** — nur bei diskreten Werten, Ausmaß angeben
3. **2D-Bins / Hexbins** — bei sehr vielen Punkten
4. **Konturlinien (2D-Dichte)** — zeigt Struktur ohne Einzelpunkte
5. **Sampling** — nur als letzte Option, und kennzeichnen

---

## 12. Small Multiples / Facetten

- **Alle Panels teilen dieselben Achsenskalen.** Freie Skalen erzeugen
  falsche Vergleiche — das ist der häufigste Fehler bei Facetten
- Panels sinnvoll sortieren (nach Wert, nicht alphabetisch)
- Maximal ~12 Panels, darüber wird es unlesbar
- Gemeinsame Legende, nicht pro Panel

---

## 13. Beschriftung und Kontext

- **Achsentitel mit Einheit.** „Vermögensanteil (%)", nicht „Anteil"
- **Aussagekräftiger Titel**, der die Kernaussage transportiert, nicht nur
  den Inhalt beschreibt: „Vermögen konzentriert sich, wo die Bevölkerung
  altert" statt „Medianalter vs. Top-10%-Anteil"
- **Direkte Beschriftung schlägt Legende**, wo der Platz es zulässt —
  spart dem Auge den Hin-und-Her-Weg
- **Quelle und Abrufdatum an jeder Grafik.** Im Dashboard als Fußzeile,
  in der Präsentation als Quellenzeile
- Zahlenformat: Tausendertrennzeichen, konsistente Nachkommastellen,
  im deutschen Kontext Dezimalkomma

---

## 14. Data-Ink und Gestaltung

Wilke widerspricht Tufte in einem Punkt: **Extremer Minimalismus ist kein
Selbstzweck.** Kontext und Orientierungshilfen dürfen Tinte kosten.

- Gitterlinien: dezent, hellgrau, nur wo sie beim Ablesen helfen
- Rahmen und Hintergründe: weg, außer sie trennen Panels
- Keine dekorativen Elemente, Verläufe, Schatten, Texturen
- Schriftgröße: in der Präsentation mindestens 14 pt bei Achsenbeschriftungen
- Konsistente Schriftart über alle Grafiken

---

## 15. Häufige Fehler — Checkliste vor Abgabe

- [ ] Balken beginnen bei Null
- [ ] Keine doppelten Y-Achsen
- [ ] Kein 3D
- [ ] Farbpalette farbfehlsichtigkeitssicher
- [ ] Farbe nicht alleiniger Informationsträger
- [ ] Kategorien nach Wert sortiert, nicht alphabetisch
- [ ] Achsen beschriftet, mit Einheit
- [ ] Facetten mit gemeinsamen Skalen
- [ ] Quelle und Abrufdatum vorhanden
- [ ] Unsicherheit dargestellt oder Fehlen begründet
- [ ] Keine Extrapolation über die Daten hinaus
- [ ] Grafik ohne Fließtext verständlich
- [ ] In Graustufen noch lesbar

---

## 16. Projektspezifisch: Alters- und Vermögensverteilung

**Bevölkerungspyramide**
- Divergierende horizontale Balken, Männer links, Frauen rechts
- **X-Achse symmetrisch und in beide Richtungen positiv beschriftet** —
  keine negativen Zahlen anzeigen
- Für Ländervergleiche: relative Anteile statt absoluter Zahlen,
  sonst dominiert die Bevölkerungsgröße

**Lorenzkurve**
- Quadratisches Seitenverhältnis (1:1), sonst verzerrt die Krümmung
- Diagonale (Gleichverteilung) als Referenz einzeichnen
- Gini-Koeffizient als Annotation, nicht als separate Grafik

**Median vs. Mittelwert (Dumbbell)**
- Nach Differenz sortieren, nicht nach Land
- Die Differenz ist die Aussage, nicht die Einzelwerte

**Scatter Medianalter × Vermögensanteil**
- Kein Kausalzusammenhang suggerieren — Regressionslinie nur mit
  Unsicherheitsband und explizitem Hinweis im Text
- **Ökologischer Fehlschluss:** Ländermittelwerte sagen nichts über
  Individuen. Gehört in die Bildunterschrift, nicht nur in den Vortrag

**Quellenvergleich (WID / OECD / UBS)**
- Dieselbe Kennzahl aus verschiedenen Quellen nebeneinander
- Zeigt, dass Daten nicht objektiv sind — starkes Methodik-Element

**Fehlende Daten**
- WID hat für viele Länder keine Vermögensreihen
- Fehlende Länder sichtbar machen (z. B. schraffiert in Karten),
  nicht stillschweigend weglassen
