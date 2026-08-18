#!/usr/bin/env python3
"""
Zet de nieuwe leveranciers en producten in de online Artikelbank.

Draai dit op een machine die hairstuff.be kan bereiken (Hairstuff01).
Het script zoekt zelf uit hoe de Artikelbank data aanneemt en gebruikt de
eerste werkende weg:

    1. een REST-API onder /wp-json/  (WordPress, custom post type)
    2. een CSV-uploadformulier op de artikelbankpagina
    3. een gewoon toevoegformulier, rij voor rij gepost

Standaard draait het in PROEFMODUS: het laat zien wat het zou doen en
schrijft niets weg. Pas met --commit gaat het werkelijk inladen.

Gebruik:
    export AB_USER='hairstuff'
    export AB_PASS='...'                 # niet in dit bestand zetten

    python3 import-artikelbank.py                 # proefdraai
    python3 import-artikelbank.py --commit        # werkelijk inladen
    python3 import-artikelbank.py --commit --alleen Barber
    python3 import-artikelbank.py --dump          # alleen structuur tonen

Vereist:  pip install requests beautifulsoup4
"""

import argparse
import csv
import glob
import json
import os
import re
import sys
from urllib.parse import urljoin

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("Ontbrekende pakketten. Draai eerst:  pip install requests beautifulsoup4")

SITE = "https://hairstuff.be/"
BANK = urljoin(SITE, "bank/artikel/")
HIER = os.path.dirname(os.path.abspath(__file__))

# Onze CSV-kolommen -> hoe ze waarschijnlijk in de Artikelbank heten.
# Het script kiest per veld de eerste naam die het in het formulier terugvindt.
VELDKANDIDATEN = {
    "Leverancier":                  ["leverancier", "supplier", "merk", "brand", "fabrikant"],
    "Categorie":                    ["categorie", "category", "groep", "productgroep", "rubriek"],
    "Voorbeeldproduct":             ["omschrijving", "naam", "titel", "artikel", "product", "title", "name"],
    "Inhoud":                       ["inhoud", "formaat", "eenheid", "verpakking", "size"],
    "Indicatieve inkoop excl":      ["inkoopprijs", "inkoop", "kostprijs", "cost", "purchase"],
    "Indicatieve salonprijs excl":  ["verkoopprijs", "verkoop", "prijs", "adviesprijs", "price"],
    "Marge %":                      ["marge", "margin"],
    "Website":                      ["website", "url", "link", "bron", "source"],
    "Land":                         ["land", "country", "herkomst"],
    "Bol geschikt":                 ["bol", "marktplaats", "marketplace"],
    "Opmerking":                    ["opmerking", "notitie", "toelichting", "note", "remark", "omschrijving_lang"],
}

# Extra velden die we altijd meesturen als het formulier ze kent. Hiermee blijft
# de Artikelbank meer dan een kopie van de webshop: deze rijen zijn kandidaten,
# geen gevoerde artikelen.
STATUS_KANDIDATEN = {
    "status":   "kandidaat",
    "herkomst": "marktanalyse 2026",
    "bron":     "marktanalyse 2026",
    "actief":   "0",
    "concept":  "1",
}


def kop(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


def inloggen(user, wachtwoord):
    """Regelt zowel basisauthenticatie als een inlogformulier."""
    s = requests.Session()
    s.headers["User-Agent"] = "Hairstuff-artikelbank-import/1.0"
    r = s.get(BANK, timeout=30, allow_redirects=True)

    if r.status_code in (401, 403):
        s.auth = (user, wachtwoord)
        r = s.get(BANK, timeout=30)

    if "login" in r.url.lower() or (r.status_code == 200 and re.search(r'type=["\']password', r.text)):
        soep = BeautifulSoup(r.text, "html.parser")
        form = soep.find("form")
        if form:
            actie = urljoin(r.url, form.get("action") or r.url)
            velden = {}
            for inp in form.find_all(["input", "select"]):
                naam = inp.get("name")
                if naam:
                    velden[naam] = inp.get("value", "")
            for k in list(velden):
                kl = k.lower()
                if any(t in kl for t in ("user", "log", "email", "naam", "gebruik")):
                    velden[k] = user
                if any(t in kl for t in ("pass", "pwd", "wacht")):
                    velden[k] = wachtwoord
            r = s.post(actie, data=velden, timeout=30, allow_redirects=True)

    if r.status_code != 200:
        sys.exit(f"Inloggen mislukt ({r.status_code}) op {r.url}")
    return s, r


def zoek_rest_api(s):
    """Kijkt of er een REST-ingang is waar artikelen in kunnen."""
    for pad in ("wp-json/", "wp-json/wp/v2/types", "api/", "bank/api/", "bank/artikel/api/"):
        url = urljoin(SITE, pad)
        try:
            r = s.get(url, timeout=15)
        except Exception:
            continue
        if r.status_code == 200 and "json" in r.headers.get("content-type", ""):
            try:
                data = r.json()
            except Exception:
                continue
            tekst = json.dumps(data)[:200000].lower()
            for sleutel in ("artikel", "bank", "product", "leverancier"):
                if sleutel in tekst:
                    return url, data
    return None, None


def zoek_formulieren(soep, basis_url):
    """Geeft alle formulieren terug met hun velden."""
    uit = []
    for f in soep.find_all("form"):
        velden = {}
        bestandsveld = None
        for inp in f.find_all(["input", "select", "textarea"]):
            naam = inp.get("name")
            if not naam:
                continue
            soort = (inp.get("type") or inp.name).lower()
            if soort == "file":
                bestandsveld = naam
            velden[naam] = {"soort": soort, "waarde": inp.get("value", "")}
        uit.append({
            "actie": urljoin(basis_url, f.get("action") or basis_url),
            "methode": (f.get("method") or "GET").upper(),
            "velden": velden,
            "bestandsveld": bestandsveld,
        })
    return uit


def maak_mapping(veldnamen):
    """Koppelt onze CSV-kolommen aan de veldnamen van het formulier."""
    laag = {v.lower(): v for v in veldnamen}
    mapping = {}
    for kolom, kandidaten in VELDKANDIDATEN.items():
        for kandidaat in kandidaten:
            for lk, echt in laag.items():
                if kandidaat in lk:
                    mapping[kolom] = echt
                    break
            if kolom in mapping:
                break
    return mapping


def lees_csvs(alleen=None):
    rijen = []
    for pad in sorted(glob.glob(os.path.join(HIER, "*.csv"))):
        with open(pad, encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh, delimiter=";"):
                if alleen and r.get("Categorie", "").lower() != alleen.lower():
                    continue
                r["_bestand"] = os.path.basename(pad)
                rijen.append(r)
    return rijen


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--commit", action="store_true", help="werkelijk inladen (standaard proefdraai)")
    p.add_argument("--alleen", help="alleen deze categorie, bijv. Barber")
    p.add_argument("--dump", action="store_true", help="alleen de structuur tonen")
    a = p.parse_args()

    user, wachtwoord = os.environ.get("AB_USER"), os.environ.get("AB_PASS")
    if not (user and wachtwoord):
        sys.exit("Zet eerst AB_USER en AB_PASS als omgevingsvariabele.")

    s, r = inloggen(user, wachtwoord)
    soep = BeautifulSoup(r.text, "html.parser")
    print(f"Ingelogd op {r.url}")

    kop("WAT DE ARTIKELBANK AANNEEMT")

    api_url, api_data = zoek_rest_api(s)
    if api_url:
        print(f"  REST-ingang gevonden: {api_url}")
    formulieren = zoek_formulieren(soep, r.url)
    print(f"  formulieren op de pagina: {len(formulieren)}")
    for i, f in enumerate(formulieren, 1):
        soorten = ", ".join(sorted({v['soort'] for v in f['velden'].values()}))
        upload = "  [CSV-UPLOAD]" if f["bestandsveld"] else ""
        print(f"    {i}. {f['methode']} {f['actie']}  ({len(f['velden'])} velden: {soorten}){upload}")
        for naam, v in list(f["velden"].items())[:25]:
            print(f"         {naam:<34} {v['soort']}")

    if a.dump:
        return

    rijen = lees_csvs(a.alleen)
    if not rijen:
        sys.exit(f"Geen CSV-regels gevonden in {HIER}"
                 + (f" voor categorie {a.alleen}" if a.alleen else ""))
    print(f"\n  te verwerken regels: {len(rijen)}")

    # ── weg 1: CSV-upload ────────────────────────────────────────────────────
    upload = next((f for f in formulieren if f["bestandsveld"]), None)
    if upload:
        kop("WEG 1 — CSV-UPLOAD")
        bestand = os.path.join(HIER, "..", "artikelbank-nieuwe-leveranciers.csv")
        bestand = os.path.normpath(bestand)
        print(f"  {upload['methode']} {upload['actie']}  veld '{upload['bestandsveld']}'")
        print(f"  bestand: {bestand}")
        if not a.commit:
            print("\n  PROEFDRAAI — niets verstuurd. Draai met --commit om te uploaden.")
            return
        extra = {k: v["waarde"] for k, v in upload["velden"].items() if v["soort"] != "file"}
        extra.update({k: v for k, v in STATUS_KANDIDATEN.items() if k in upload["velden"]})
        with open(bestand, "rb") as fh:
            resp = s.post(upload["actie"], data=extra,
                          files={upload["bestandsveld"]: (os.path.basename(bestand), fh, "text/csv")},
                          timeout=120)
        print(f"  -> {resp.status_code}")
        print("  " + BeautifulSoup(resp.text, "html.parser").get_text()[:600].strip().replace("\n", "\n  "))
        return

    # ── weg 2: rij voor rij posten ───────────────────────────────────────────
    invoer = [f for f in formulieren
              if f["methode"] == "POST" and len(f["velden"]) >= 3
              and not any("pass" in n.lower() or "zoek" in n.lower() or "search" in n.lower()
                          for n in f["velden"])]
    if not invoer:
        kop("GEEN INVOERWEG GEVONDEN")
        print("""  Er is geen uploadveld en geen bruikbaar invoerformulier gevonden.
  Waarschijnlijk is de Artikelbank alleen-lezen en wordt hij gevuld vanuit de
  webshop of vanuit Mplus. Dan zijn er twee mogelijkheden:

    a. de bron aanvullen  -- zet de nieuwe artikelen in de webshop of in Mplus
       als concept, dan komen ze vanzelf in de bank terecht;
    b. de bank uitbreiden -- laat de Artikelbank ook records aannemen die geen
       webshopartikel zijn, met een veld 'status' (kandidaat / in onderhandeling
       / gevoerd) en 'herkomst'.

  Stuur de uitvoer van dit script door, dan is te zien welke van de twee kan.""")
        return

    form = invoer[0]
    mapping = maak_mapping(form["velden"].keys())
    kop("WEG 2 — RIJ VOOR RIJ")
    print(f"  {form['methode']} {form['actie']}")
    print("  koppeling van kolommen aan formuliervelden:")
    for kolom in VELDKANDIDATEN:
        print(f"    {kolom:<30} -> {mapping.get(kolom, '(geen veld gevonden)')}")
    niet = [k for k in VELDKANDIDATEN if k not in mapping]
    if niet:
        print(f"\n  LET OP: {len(niet)} kolommen konden niet gekoppeld worden.")

    ok = mis = 0
    for i, rij in enumerate(rijen, 1):
        lading = {k: v["waarde"] for k, v in form["velden"].items() if v["soort"] not in ("submit", "file")}
        for kolom, veld in mapping.items():
            lading[veld] = rij.get(kolom, "")
        for k, v in STATUS_KANDIDATEN.items():
            for veld in form["velden"]:
                if k in veld.lower():
                    lading[veld] = v
        etiket = f"{rij.get('Categorie','?')} / {rij.get('Leverancier','?')}"
        if not a.commit:
            if i <= 3:
                print(f"\n  [proef {i}] {etiket}")
                for k, v in lading.items():
                    if v:
                        print(f"      {k:<30} = {str(v)[:52]}")
            continue
        try:
            resp = s.post(form["actie"], data=lading, timeout=60)
            if resp.status_code < 400:
                ok += 1
                print(f"  [{i:>3}/{len(rijen)}] ok   {etiket}")
            else:
                mis += 1
                print(f"  [{i:>3}/{len(rijen)}] FOUT {resp.status_code}  {etiket}")
        except Exception as e:
            mis += 1
            print(f"  [{i:>3}/{len(rijen)}] FOUT {type(e).__name__}  {etiket}")

    if not a.commit:
        print(f"\n  PROEFDRAAI — niets verstuurd ({len(rijen)} regels klaar).")
        print("  Controleer de koppeling hierboven en draai dan met --commit.")
    else:
        print(f"\n  klaar: {ok} geplaatst, {mis} mislukt")


if __name__ == "__main__":
    main()
