#!/usr/bin/env python3
"""
Stap 1 van twee: verkennen hoe de Artikelbank werkt.

Draai dit op Hairstuff01 (of een andere machine die hairstuff.be kan bereiken).
Het script logt in, haalt de artikelbankpagina op en rapporteert welke velden,
formulieren en endpoints het vindt. Het schrijft niets weg en verandert niets.

Plak de uitvoer terug in het gesprek; daarmee kan de importmapping worden
afgemaakt en volgt stap 2, het script dat werkelijk laadt.

Gebruik:
    export AB_USER='hairstuff'
    export AB_PASS='...'            # niet in dit bestand zetten
    python3 verken-artikelbank.py

Vereist:  pip install requests beautifulsoup4
"""

import json
import os
import sys
from urllib.parse import urljoin

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("Ontbrekende pakketten. Draai eerst:  pip install requests beautifulsoup4")

BASIS = "https://hairstuff.be/bank/artikel/"
USER = os.environ.get("AB_USER")
PASS = os.environ.get("AB_PASS")

if not (USER and PASS):
    sys.exit("Zet eerst AB_USER en AB_PASS als omgevingsvariabele.")


def kop(tekst):
    print("\n" + "=" * 78)
    print(tekst)
    print("=" * 78)


s = requests.Session()
s.headers["User-Agent"] = "Hairstuff-artikelbank-verkenner/1.0"

# ── 1. Hoe wordt er geauthenticeerd? ─────────────────────────────────────────
kop("1. AUTHENTICATIE")

r = s.get(BASIS, timeout=30, allow_redirects=True)
print(f"  GET {BASIS} -> {r.status_code}, eindigt op {r.url}")

if r.status_code == 401:
    print("  Server vraagt HTTP-basisauthenticatie; opnieuw met inloggegevens.")
    s.auth = (USER, PASS)
    r = s.get(BASIS, timeout=30)
    print(f"  opnieuw -> {r.status_code}")
elif "login" in r.url.lower() or "wp-login" in r.url.lower():
    print("  Server stuurt door naar een inlogformulier; proberen te posten.")
    soep = BeautifulSoup(r.text, "html.parser")
    form = soep.find("form")
    if form:
        actie = urljoin(r.url, form.get("action") or r.url)
        velden = {}
        for inp in form.find_all(["input", "select"]):
            naam = inp.get("name")
            if not naam:
                continue
            velden[naam] = inp.get("value", "")
        # vul de meest gangbare veldnamen
        for k in list(velden):
            kl = k.lower()
            if any(t in kl for t in ("user", "log", "email", "naam")):
                velden[k] = USER
            if any(t in kl for t in ("pass", "pwd", "wacht")):
                velden[k] = PASS
        print(f"  POST {actie} met velden: {sorted(velden)}")
        r = s.post(actie, data=velden, timeout=30)
        print(f"  -> {r.status_code}, eindigt op {r.url}")

if r.status_code != 200:
    print(f"\n  Inloggen lijkt niet gelukt ({r.status_code}). Eerste 400 tekens:\n")
    print("  " + r.text[:400].replace("\n", "\n  "))
    sys.exit(1)

print("  Ingelogd.")

# ── 2. Wat staat er op de pagina? ────────────────────────────────────────────
kop("2. PAGINASTRUCTUUR")

soep = BeautifulSoup(r.text, "html.parser")
print(f"  titel: {soep.title.string.strip() if soep.title else '(geen)'}")

formulieren = soep.find_all("form")
print(f"  formulieren gevonden: {len(formulieren)}")
for i, f in enumerate(formulieren, 1):
    actie = f.get("action") or "(zelfde pagina)"
    methode = (f.get("method") or "GET").upper()
    print(f"\n  --- formulier {i}: {methode} {actie}")
    for inp in f.find_all(["input", "select", "textarea"]):
        naam = inp.get("name")
        if not naam:
            continue
        soort = inp.get("type") or inp.name
        verplicht = " VERPLICHT" if inp.has_attr("required") else ""
        opties = ""
        if inp.name == "select":
            opties = " | opties: " + ", ".join(
                o.get("value", o.text.strip())[:24] for o in inp.find_all("option")[:12]
            )
        print(f"      {naam:<32} {soort:<10}{verplicht}{opties}")

# ── 3. Is er een upload- of API-ingang? ──────────────────────────────────────
kop("3. UPLOAD- EN API-INGANGEN")

bestand_velden = [
    inp.get("name")
    for f in formulieren
    for inp in f.find_all("input")
    if (inp.get("type") or "").lower() == "file"
]
print(f"  bestandsvelden: {bestand_velden or '(geen)'}")

kandidaten = [
    "wp-json/", "api/", "bank/api/", "bank/artikel/api/",
    "bank/artikel/import/", "bank/artikel/export/", "bank/import/",
]
for pad in kandidaten:
    url = urljoin("https://hairstuff.be/", pad)
    try:
        p = s.get(url, timeout=15)
        soort = p.headers.get("content-type", "")[:40]
        merk = "  <-- bekijken" if p.status_code == 200 else ""
        print(f"  {p.status_code}  {url:<48} {soort}{merk}")
    except Exception as e:
        print(f"  ---  {url:<48} {type(e).__name__}")

# ── 4. Bestaande records als voorbeeld ───────────────────────────────────────
kop("4. VOORBEELD VAN EEN BESTAAND RECORD")

tabellen = soep.find_all("table")
print(f"  tabellen op de pagina: {len(tabellen)}")
if tabellen:
    t = tabellen[0]
    koppen = [th.get_text(strip=True) for th in t.find_all("th")]
    print(f"  kolomkoppen: {koppen}")
    rij = t.find("tbody").find("tr") if t.find("tbody") else None
    if rij:
        print(f"  eerste rij : {[td.get_text(strip=True)[:28] for td in rij.find_all('td')]}")

links = {a.get("href") for a in soep.find_all("a", href=True)}
interessant = sorted(
    l for l in links
    if any(t in l.lower() for t in ("import", "export", "csv", "nieuw", "toevoegen", "add"))
)
print(f"\n  links die op importeren of toevoegen wijzen:")
for l in interessant[:15]:
    print(f"    {l}")

kop("KLAAR")
print("""  Plak de uitvoer hierboven terug in het gesprek. Op basis daarvan volgt
  stap 2: het script dat de CSV's uit deze map werkelijk inleest, met de
  juiste veldnamen en als concept in plaats van live.""")
