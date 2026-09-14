"""
Aufbereitung der Rohdaten zu den Parquet-Dateien in `data/processed/`.

Erzeugt (siehe Spezifikation Abschnitt 5):
- laender_jahr.parquet   Land × Jahr: Demografie (WPP) + Vermögen (WID)
- pyramide.parquet       Land × Jahr × Altersgruppe × Geschlecht
- wid_dezile.parquet     Land × Jahr × Dezil, für Lorenzkurven
- wid_qualitaet.parquet  Land: Qualitätskennzahlen und Quellen
- join_protokoll.csv     nicht gematchte Codes beider Seiten
- wid_lang.parquet       Zwischencache: gefilterte WID-Rohdaten (lang)

Jeder Filter und Merge gibt Zeilenzahlen auf der Konsole aus, damit sich
die Aufbereitung nachvollziehen lässt (Spezifikation Abschnitt 8).

Aufruf:  uv run python -m src.clean
"""

import re

import pandas as pd

from src.load import (
    BELASTBAR,
    DEZILE,
    GRUPPEN,
    VAR_ANTEIL,
    VAR_MITTEL,
    VAR_PPP,
    VAR_PREISINDEX,
    VAR_SCHWELLE,
    VERARBEITET,
    lade_wid_daten,
    lade_wid_laender,
    lade_wid_metadaten,
    lade_wpp_altersgruppen,
    lade_wpp_indikatoren,
)

# Zeitraum des Projekts (Spezifikation Abschnitt 4 und 9).
JAHR_VON = 1975
JAHR_BIS = 2050
PROJEKTION_AB = 2024  # ab hier sind WPP-Werte Projektionen (Medium)

# Kontinente heißen bei WPP und WID gleich; wir übersetzen einmal ins Deutsche.
REGION_DE = {
    "Africa": "Afrika",
    "Americas": "Amerika",
    "Asia": "Asien",
    "Europe": "Europa",
    "Oceania": "Ozeanien",
}

# WPP verweist bei Bermuda, Kanada, Grönland, St. Pierre & Miquelon und den
# USA auf die ParentID 918 („Northern America" der alten Gliederung), die in
# der Indikatorendatei selbst nicht vorkommt. Wir hängen sie an „Americas".
ELTERN_FEHLEND = {918: 5505}

# WID führt Kosovo zweimal: „KS" (mit Vermögensreihe, kein ISO-Code) und
# „XK" (ohne Reihe, der Code, den auch WPP nutzt). Wir vereinheitlichen auf XK.
KOSOVO = {"KS": "XK"}

# Perzentilgruppe -> Spaltenname im Datenmodell
GRUPPEN_SPALTEN = {
    "p90p100": "top10",
    "p99p100": "top1",
    "p0p50": "bottom50",
    "p50p90": "mittel50_90",
}


def melde(schritt: str, vorher: int, nachher: int) -> None:
    """Einheitliche Konsolenzeile für jeden Filter- oder Merge-Schritt."""
    print(f"  {schritt}: {vorher:,} -> {nachher:,} Zeilen")


# --- WPP -------------------------------------------------------------------
def wpp_regionen(ind: pd.DataFrame) -> pd.Series:
    """Ordnet jeder LocID den Kontinent zu, indem die ParentID-Kette nach oben
    gelaufen wird, bis ein Kontinent erreicht ist.

    WPP-Länder hängen meist an einer Subregion, die an einem Kontinent hängt.
    Nordamerika ist die Ausnahme: USA, Kanada usw. hängen direkt an
    „Northern America", das wiederum an „Americas" hängt. Deshalb keine feste
    Anzahl Schritte, sondern eine Schleife.
    """
    orte = ind.drop_duplicates("LocID").set_index("LocID")
    eltern = orte["ParentID"].to_dict() | ELTERN_FEHLEND
    namen = orte["Location"].to_dict()
    kontinente = set(REGION_DE)

    def kontinent(loc_id: int) -> str | None:
        aktuell = loc_id
        for _ in range(10):  # Schutz gegen Endlosschleifen
            if namen.get(aktuell) in kontinente:
                return REGION_DE[namen[aktuell]]
            aktuell = eltern.get(aktuell)
            if aktuell is None or pd.isna(aktuell):
                return None
            aktuell = int(aktuell)
        return None

    laender = orte[orte["LocTypeName"] == "Country/Area"].index
    return pd.Series({loc: kontinent(loc) for loc in laender}, name="region")


def wpp_laender_jahr(ind: pd.DataFrame) -> pd.DataFrame:
    """Demografische Kennzahlen pro Land und Jahr, 1975–2050, umbenannt."""
    print("WPP Indikatoren:")
    n0 = len(ind)
    print("  LocTypeName:", ind["LocTypeName"].value_counts(dropna=False).to_dict())
    laender = ind[ind["LocTypeName"] == "Country/Area"]
    melde("Filter Country/Area", n0, len(laender))

    n1 = len(laender)
    laender = laender[laender["Time"].between(JAHR_VON, JAHR_BIS)]
    melde(f"Filter Jahre {JAHR_VON}–{JAHR_BIS}", n1, len(laender))

    regionen = wpp_regionen(ind)
    df = laender.rename(
        columns={
            "ISO2_code": "iso2",
            "ISO3_code": "iso3",
            "Location": "land",
            "Time": "jahr",
            "TPopulation1July": "bevoelkerung_tsd",
            "MedianAgePop": "medianalter",
            "TFR": "fertilitaet",
            "LEx": "lebenserwartung",
            "LE65": "lebenserwartung_65",
        }
    )
    df["region"] = df["LocID"].map(regionen)
    df["projektion"] = df["jahr"] >= PROJEKTION_AB
    print(f"  Länder: {df['iso2'].nunique()}, ohne Region: {df['region'].isna().sum()}")
    return df[
        [
            "iso2",
            "iso3",
            "land",
            "region",
            "jahr",
            "projektion",
            "bevoelkerung_tsd",
            "medianalter",
            "fertilitaet",
            "lebenserwartung",
            "lebenserwartung_65",
        ]
    ].reset_index(drop=True)


def wpp_pyramide(alter: pd.DataFrame) -> pd.DataFrame:
    """Langes Format für Bevölkerungspyramiden: eine Zeile je Land, Jahr,
    Altersgruppe und Geschlecht. `anteil` bezieht sich auf die
    Gesamtbevölkerung des Landes im jeweiligen Jahr (Stichtag 1. Januar)."""
    print("WPP Altersgruppen:")
    n0 = len(alter)
    laender = alter[alter["LocTypeName"] == "Country/Area"]
    melde("Filter Country/Area", n0, len(laender))
    n1 = len(laender)
    laender = laender[laender["Time"].between(JAHR_VON, JAHR_BIS)]
    melde(f"Filter Jahre {JAHR_VON}–{JAHR_BIS}", n1, len(laender))

    lang = laender.melt(
        id_vars=["ISO3_code", "Time", "AgeGrp", "AgeGrpStart"],
        value_vars=["PopMale", "PopFemale"],
        var_name="geschlecht",
        value_name="bevoelkerung_tsd",
    )
    lang["geschlecht"] = lang["geschlecht"].map({"PopMale": "m", "PopFemale": "w"})
    lang = lang.rename(
        columns={
            "ISO3_code": "iso3",
            "Time": "jahr",
            "AgeGrp": "altersgruppe",
            "AgeGrpStart": "altersgruppe_start",
        }
    )
    gesamt = lang.groupby(["iso3", "jahr"])["bevoelkerung_tsd"].transform("sum")
    lang["anteil"] = lang["bevoelkerung_tsd"] / gesamt
    melde("Umformung lang (× 2 Geschlechter)", len(laender), len(lang))
    return lang.reset_index(drop=True)


def wpp_oadr(alter: pd.DataFrame) -> pd.DataFrame:
    """Altersabhängigkeitsquotient: Bevölkerung 65+ geteilt durch 15–64,
    aus der Altersgruppen-Datei (Stichtag 1. Januar). Als Verhältnis
    gespeichert (0,3 = 30 Personen 65+ je 100 im Erwerbsalter)."""
    laender = alter[alter["LocTypeName"] == "Country/Area"]
    alt = (
        laender[laender["AgeGrpStart"] >= 65]
        .groupby(["ISO3_code", "Time"])["PopTotal"]
        .sum()
    )
    erwerb = (
        laender[laender["AgeGrpStart"].between(15, 60)]
        .groupby(["ISO3_code", "Time"])["PopTotal"]
        .sum()
    )
    oadr = (alt / erwerb).rename("oadr").reset_index()
    return oadr.rename(columns={"ISO3_code": "iso3", "Time": "jahr"})


# --- WID -------------------------------------------------------------------
def kosovo_vereinheitlichen(
    wid: pd.DataFrame, meta: pd.DataFrame, laender: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Ersetzt den WID-Code KS durch XK und entfernt den doppelten
    Länderlisten-Eintrag, damit Kosovo genau einmal vorkommt und an WPP passt."""
    n = len(laender)
    laender = laender[~laender["alpha2"].isin(KOSOVO)]
    melde("Kosovo: doppelten Eintrag KS aus Länderliste entfernt", n, len(laender))
    wid = wid.assign(country=wid["country"].replace(KOSOVO))
    meta = meta.assign(country=meta["country"].replace(KOSOVO))
    return wid, meta, laender.reset_index(drop=True)


def wid_breit(wid: pd.DataFrame) -> pd.DataFrame:
    """Vermögenskennzahlen pro Land und Jahr, eine Spalte je Kennzahl.

    Neben den Werten in lokaler Währung (`ahweal`, `median_weal`) gibt es
    kaufkraftbereinigte Werte in US-Dollar (`_ppp_usd`). Dafür wird die
    PPP-Rate des letzten verfügbaren Jahres eines Landes verwendet, weil
    WID die Vermögen in konstanten Preisen ausweist.
    """
    print("WID Umformung breit:")
    n0 = len(wid)
    anteile = wid[(wid["variable"] == VAR_ANTEIL) & wid["percentile"].isin(GRUPPEN)]
    breit = (
        anteile.pivot(index=["country", "year"], columns="percentile", values="value")
        .rename(columns=GRUPPEN_SPALTEN)
        .reset_index()
    )
    melde("Anteile Gruppen (pivot)", len(anteile), len(breit))

    # Qualität der Top-10-%-Reihe. Prüfung: identisch über alle Perzentile?
    je_jahr = anteile.groupby(["country", "year"])["data_quality"].nunique(dropna=False)
    print(
        f"  Jahre mit uneinheitlicher Qualität über Perzentile: {(je_jahr > 1).sum()}"
    )
    quality = anteile[anteile["percentile"] == "p90p100"][
        ["country", "year", "data_quality"]
    ]
    breit = breit.merge(
        quality.rename(columns={"data_quality": "quality_top10"}),
        on=["country", "year"],
        how="left",
        validate="one_to_one",
    )

    mittel = wid[(wid["variable"] == VAR_MITTEL) & (wid["percentile"] == "p0p100")]
    breit = breit.merge(
        mittel[["country", "year", "value"]].rename(columns={"value": "ahweal"}),
        on=["country", "year"],
        how="left",
        validate="one_to_one",
    )

    # Median = Schwelle, ab der man zur oberen Hälfte gehört.
    schwellen = wid[wid["variable"] == VAR_SCHWELLE]
    median = schwellen[schwellen["percentile"] == "p50p100"]
    kontrolle = schwellen[schwellen["percentile"] == "p50p51"]
    vergleich = median.merge(kontrolle, on=["country", "year"], suffixes=("_a", "_b"))
    abweichung = (vergleich["value_a"] - vergleich["value_b"]).abs().max()
    print(f"  Median p50p100 vs. p50p51: max. Abweichung {abweichung:.6f}")
    breit = breit.merge(
        median[["country", "year", "value"]].rename(columns={"value": "median_weal"}),
        on=["country", "year"],
        how="left",
        validate="one_to_one",
    )

    # PPP-Rate: letzter verfügbarer Wert je Land, auf alle Jahre angewendet.
    # Das ist nur richtig, wenn dieses Jahr das Preisbasisjahr der
    # Vermögensreihen ist (WID weist Vermögen in konstanten Preisen aus;
    # der Preisindex inyixxi999 ist im Basisjahr exakt 1). Stimmt das nicht
    # mehr, z. B. nach einem WID-Update, bricht die Aufbereitung hier ab.
    ppp = wid[wid["variable"] == VAR_PPP].sort_values("year")
    ppp = ppp.groupby("country").agg(
        ppp_usd=("value", "last"), ppp_jahr=("year", "last")
    )
    index = wid[wid["variable"] == VAR_PREISINDEX]
    basisjahr = (
        index[(index["value"] - 1).abs() < 1e-9].groupby("country")["year"].max()
    ).rename("basisjahr")
    ppp = ppp.join(basisjahr)
    abweichend = ppp[ppp["ppp_jahr"] != ppp["basisjahr"]]
    assert abweichend.empty, (
        "PPP-Jahr entspricht nicht dem Preisbasisjahr (inyixxi999 == 1):\n"
        f"{abweichend.to_string()}"
    )
    print(
        f"  PPP-Jahr = Preisbasisjahr {sorted(int(j) for j in ppp['basisjahr'].unique())} "
        f"für {len(ppp)} Länder"
    )
    breit["ppp_usd"] = breit["country"].map(ppp["ppp_usd"])
    breit["ahweal_ppp_usd"] = breit["ahweal"] / breit["ppp_usd"]
    breit["median_weal_ppp_usd"] = breit["median_weal"] / breit["ppp_usd"]
    print(
        f"  Länder ohne PPP-Rate: {breit.loc[breit['ppp_usd'].isna(), 'country'].nunique()}"
    )

    breit = breit.rename(columns={"country": "iso2", "year": "jahr"})
    melde("Ergebnis", n0, len(breit))
    return breit


def wid_dezile(wid: pd.DataFrame) -> pd.DataFrame:
    """Dezilanteile pro Land und Jahr für Lorenzkurven, inklusive Qualität."""
    dez = wid[(wid["variable"] == VAR_ANTEIL) & wid["percentile"].isin(DEZILE)].copy()
    dez["dezil"] = dez["percentile"].map({p: i + 1 for i, p in enumerate(DEZILE)})
    dez = dez.rename(
        columns={
            "country": "iso2",
            "year": "jahr",
            "value": "anteil",
            "data_quality": "quality",
        }
    )
    dez = dez[["iso2", "jahr", "dezil", "anteil", "quality"]].sort_values(
        ["iso2", "jahr", "dezil"]
    )
    vollstaendig = dez.groupby(["iso2", "jahr"])["dezil"].count()
    print(
        f"WID Dezile: {len(dez):,} Zeilen, {vollstaendig.eq(10).sum():,} vollständige "
        f"Land-Jahre, {vollstaendig.ne(10).sum()} unvollständige"
    )
    return dez.reset_index(drop=True)


def quellen_kurz(source: str) -> str:
    """Zieht aus dem WID-Quellenfeld die lesbaren Zitate heraus.

    Das Feld hat die Form `[URL][URL_LINK]…[/URL_LINK][URL_TEXT]Zitat[/URL_TEXT][/URL]`,
    oft mehrfach hintereinander. Wir behalten nur die Zitat-Teile.
    """
    if not isinstance(source, str):
        return ""
    zitate = re.findall(r"\[URL_TEXT\](.*?)\[/URL_TEXT\]", source, flags=re.DOTALL)
    zitate = [" ".join(z.split()).strip("; ") for z in zitate]
    return " | ".join(z for z in zitate if z)


def wpp_regionen_iso2(ind: pd.DataFrame) -> pd.Series:
    """Kontinent je ISO2-Code aus der WPP-Hierarchie (Index iso2)."""
    regionen = wpp_regionen(ind)
    laender = ind[ind["LocTypeName"] == "Country/Area"].drop_duplicates("LocID")
    return pd.Series(
        laender["LocID"].map(regionen).values, index=laender["ISO2_code"], name="region"
    )


def wid_qualitaet(
    wid: pd.DataFrame,
    meta: pd.DataFrame,
    laender: pd.DataFrame,
    regionen_wpp: pd.Series,
) -> pd.DataFrame:
    """Qualitätskennzahlen je WID-Land, berechnet auf der Top-10-%-Reihe
    von `shwealj992` (die Qualität ist je Jahr über alle Perzentile gleich).

    Basis ist die vollständige WID-Länderliste, damit auch Länder ohne
    Vermögensdaten auftauchen (`hat_daten == False`).

    Die Region kommt aus der WPP-Hierarchie (`regionen_wpp`, Index iso2),
    damit alle Ausgaben dieselbe Einteilung nutzen. WID weicht bei Zypern,
    Belarus, Russland und der Ukraine ab. Nur Länder ohne WPP-Eintrag
    (historische Staaten) behalten die WID-Region.
    """
    reihe = wid[(wid["variable"] == VAR_ANTEIL) & (wid["percentile"] == "p90p100")]
    belastbar = reihe[reihe["data_quality"] >= BELASTBAR]

    kennzahlen = reihe.groupby("country").agg(
        jahr_von=("year", "min"),
        jahr_bis=("year", "max"),
        n_jahre=("year", "count"),
        max_quality=("data_quality", "max"),
        anteil_quality_0=("data_quality", lambda q: (q == 0).mean()),
    )
    bel = belastbar.groupby("country").agg(
        erstes_belastbares_jahr=("year", "min"),
        letztes_belastbares_jahr=("year", "max"),
        n_jahre_belastbar=("year", "count"),
    )
    kennzahlen = kennzahlen.join(bel)
    kennzahlen["n_jahre_belastbar"] = (
        kennzahlen["n_jahre_belastbar"].fillna(0).astype(int)
    )

    quellen = meta.set_index("country")
    kennzahlen["avg_quality"] = quellen["avg_quality"]
    kennzahlen["quellen"] = quellen["source"].map(quellen_kurz)
    # Länder, deren Quellen ausschließlich das Imputationspapier sind (es wird
    # meist zweimal zitiert: Fassung 2021 und Aktualisierung 2025).
    kennzahlen["nur_imputation"] = kennzahlen["quellen"].map(
        lambda s: bool(s) and all("mputation" in teil for teil in s.split(" | "))
    )

    df = laender[["alpha2", "shortname", "region"]].rename(
        columns={"alpha2": "iso2", "shortname": "land_wid"}
    )
    region_wid = df["region"].map(REGION_DE).fillna(df["region"])
    df["region"] = df["iso2"].map(regionen_wpp).fillna(region_wid)
    print(
        f"  Region aus WPP: {df['iso2'].isin(regionen_wpp.index).sum()} Länder, "
        f"aus WID (kein WPP-Eintrag): {(~df['iso2'].isin(regionen_wpp.index)).sum()}"
    )
    df = df.merge(
        kennzahlen, left_on="iso2", right_index=True, how="left", indicator=True
    )
    df["hat_daten"] = df["_merge"] == "both"
    print(
        "WID Qualität, Merge Länderliste × Kennzahlen:",
        df["_merge"].value_counts().to_dict(),
    )
    return df.drop(columns="_merge").reset_index(drop=True)


# --- Join ------------------------------------------------------------------
def join(wpp: pd.DataFrame, wid: pd.DataFrame, wid_laender: pd.DataFrame) -> tuple:
    """Hängt die WID-Kennzahlen links an die WPP-Basis. Länder ohne
    Vermögensdaten bleiben erhalten. Gibt (laender_jahr, protokoll) zurück."""
    print("Join WPP × WID (left, Schlüssel iso2 + jahr):")
    df = wpp.merge(
        wid, on=["iso2", "jahr"], how="left", indicator=True, validate="one_to_one"
    )
    print("  _merge:", df["_merge"].value_counts().to_dict())
    print(
        f"  Länder gesamt: {df['iso2'].nunique()}, "
        f"mit Vermögensdaten: {df.loc[df['_merge'] == 'both', 'iso2'].nunique()}"
    )

    # Protokoll: Codes, die nur auf einer Seite vorkommen.
    wpp_codes = set(wpp["iso2"])
    wid_mit_daten = set(wid["iso2"])
    wid_alle = set(wid_laender["alpha2"])
    namen_wpp = wpp.drop_duplicates("iso2").set_index("iso2")["land"]
    namen_wid = wid_laender.set_index("alpha2")["shortname"]

    zeilen = []
    for code in sorted(wpp_codes - wid_alle):
        zeilen.append(
            {
                "code": code,
                "name": namen_wpp[code],
                "seite": "nur_wpp",
                "hinweis": "kein Eintrag in WID_countries",
            }
        )
    for code in sorted(wpp_codes & wid_alle - wid_mit_daten):
        zeilen.append(
            {
                "code": code,
                "name": namen_wpp[code],
                "seite": "beide",
                "hinweis": "in WID gelistet, aber ohne Vermögensreihe",
            }
        )
    for code in sorted(wid_alle - wpp_codes):
        zeilen.append(
            {
                "code": code,
                "name": namen_wid[code],
                "seite": "nur_wid",
                "hinweis": "mit Vermögensreihe"
                if code in wid_mit_daten
                else "ohne Vermögensreihe",
            }
        )
    protokoll = pd.DataFrame(zeilen)
    print(f"  Protokoll: {protokoll['seite'].value_counts().to_dict()}")
    return df.drop(columns="_merge"), protokoll


# --- Validierung -------------------------------------------------------------
def validiere(lj: pd.DataFrame, dez: pd.DataFrame) -> None:
    """Plausibilitätsprüfungen nach Spezifikation Abschnitt 8."""
    print("Validierung:")
    mit = lj.dropna(subset=["top10"])
    summe = mit["bottom50"] + mit["mittel50_90"] + mit["top10"]
    toleranz = 0.005
    print(
        f"  Summe bottom50+mittel50_90+top10: min {summe.min():.4f}, max {summe.max():.4f}, "
        f"außerhalb 1±{toleranz}: {(~summe.between(1 - toleranz, 1 + toleranz)).sum()}"
    )
    dezsumme = dez.groupby(["iso2", "jahr"])["anteil"].sum()
    print(
        f"  Summe Dezile: min {dezsumme.min():.4f}, max {dezsumme.max():.4f}, "
        f"außerhalb 1±{toleranz}: {(~dezsumme.between(1 - toleranz, 1 + toleranz)).sum()}"
    )
    for spalte, lo, hi in [
        ("top10", 0, 1),
        ("top1", 0, 1),
        ("bottom50", -0.2, 1),
        ("mittel50_90", 0, 1),
        # Spez.: 10–60; Heiliger Stuhl (ab 2009) und Hongkong (ab 2047) liegen bei 62
        ("medianalter", 10, 65),
        ("oadr", 0, 1.5),
        ("quality_top10", 0, 5),
    ]:
        s = lj[spalte].dropna()
        drinnen = s.between(lo, hi).all()
        print(
            f"  {spalte}: {s.min():.3f} bis {s.max():.3f} "
            f"({'ok' if drinnen else 'AUSSERHALB'} {lo}–{hi})"
        )
        if not drinnen:
            raus = lj.loc[~lj[spalte].between(lo, hi) & lj[spalte].notna()]
            print(
                "    betroffen:",
                raus.groupby("land")["jahr"].agg(["min", "max"]).to_dict("index"),
            )
    print(
        f"  Jahre: {lj['jahr'].min()}–{lj['jahr'].max()}, "
        f"WID-Jahre: {int(mit['jahr'].min())}–{int(mit['jahr'].max())}"
    )
    print(
        "  Qualität Top 10 % (Land-Jahre):",
        lj["quality_top10"].value_counts(dropna=False).sort_index().to_dict(),
    )


# --- Hauptprogramm -----------------------------------------------------------
def main() -> None:
    VERARBEITET.mkdir(parents=True, exist_ok=True)

    # WPP
    ind = lade_wpp_indikatoren()
    alter = lade_wpp_altersgruppen()
    wpp = wpp_laender_jahr(ind)
    pyramide = wpp_pyramide(alter)
    oadr = wpp_oadr(alter)
    n = len(wpp)
    wpp = wpp.merge(oadr, on=["iso3", "jahr"], how="left", validate="one_to_one")
    melde("Merge OADR an Indikatoren", n, len(wpp))
    print(f"  Zeilen ohne OADR: {wpp['oadr'].isna().sum()}")

    # WID: Rohdaten einmal lesen und als Cache ablegen
    wid_laender = lade_wid_laender()
    print(f"WID Länderliste: {len(wid_laender)} echte Länder (alpha2 mit 2 Zeichen)")
    cache = VERARBEITET / "wid_lang.parquet"
    if cache.exists():
        wid = pd.read_parquet(cache)
        print(f"WID: Cache gelesen, {len(wid):,} Zeilen")
    else:
        wid = lade_wid_daten(wid_laender["alpha2"].tolist())
        wid.to_parquet(cache, index=False)
    n = len(wid)
    wid = wid[wid["year"].between(JAHR_VON, JAHR_BIS)]
    melde(f"WID Filter Jahre {JAHR_VON}–{JAHR_BIS}", n, len(wid))
    meta = lade_wid_metadaten(wid_laender["alpha2"].tolist())
    print(f"WID Metadaten: {len(meta)} Länder mit Eintrag zu {VAR_ANTEIL}")
    wid, meta, wid_laender = kosovo_vereinheitlichen(wid, meta, wid_laender)

    breit = wid_breit(wid)
    dezile = wid_dezile(wid)
    qualitaet = wid_qualitaet(wid, meta, wid_laender, wpp_regionen_iso2(ind))

    laender_jahr, protokoll = join(wpp, breit, wid_laender)
    validiere(laender_jahr, dezile)

    # Schreiben
    laender_jahr.to_parquet(VERARBEITET / "laender_jahr.parquet", index=False)
    pyramide.to_parquet(VERARBEITET / "pyramide.parquet", index=False)
    dezile.to_parquet(VERARBEITET / "wid_dezile.parquet", index=False)
    qualitaet.to_parquet(VERARBEITET / "wid_qualitaet.parquet", index=False)
    protokoll.to_csv(VERARBEITET / "join_protokoll.csv", index=False)
    print("Geschrieben nach", VERARBEITET)
    for name, df in [
        ("laender_jahr", laender_jahr),
        ("pyramide", pyramide),
        ("wid_dezile", dezile),
        ("wid_qualitaet", qualitaet),
    ]:
        print(f"  {name}.parquet: {len(df):,} Zeilen, {len(df.columns)} Spalten")


if __name__ == "__main__":
    main()
