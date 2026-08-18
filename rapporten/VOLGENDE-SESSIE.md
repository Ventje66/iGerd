# Overdracht — Hairstuff marktanalyse

Bedoeld om in een volgende sessie meteen verder te kunnen. Lees dit eerst,
dan hoeft niets opnieuw uitgezocht te worden.

**Laatst bijgewerkt:** 10 augustus 2026
**Branch:** `claude/market-analysis-recommendations-8yh8uj`
**Pull request:** [#4](https://github.com/Ventje66/iGerd/pull/4) (draft)
**Rapport online:** https://claude.ai/code/artifact/8cf5a57d-66fd-4c1d-91b4-df7ba81a5dbd

---

## 1. Waar het over gaat

The HairStuff Company (Gert, Malle) is een kappersgroothandel met één winkel en
één webshop. Gevraagd is een marktanalyse met groeiplan: nieuwe leveranciers,
nieuwe markten, nieuwe producten, een Bol-winkel, en uitbreiding van het eigen
merk — concreet onderbouwd, met bronvermelding, en bruikbaar om korte-,
middellange- en langetermijnplannen op te baseren.

**Over Gert:** commercieel verkoper, geen durver. Werkt met cijfers en concrete
voorbeelden, niet met abstracties. Elk voorstel heeft daarom een kleinste test
met prijskaartje en een regel over wat je verliest als het misgaat.

---

## 2. Bestanden in deze repo

| Pad | Wat |
|---|---|
| `rapporten/hairstuff-marktanalyse-2026.html` | Het rapport. Zelfstandige HTML, licht/donker-thema, eigen print-stylesheet |
| `rapporten/Hairstuff-Marktanalyse-2026.pdf` | 41 pagina's A4 |
| `rapporten/build-pdf.sh` | Rendert de PDF opnieuw na een wijziging in de HTML |
| `rapporten/analyse/` | Scripts waarmee alle Mplus-cijfers narekenbaar zijn |
| `rapporten/artikelbank/` | 11 CSV's, 105 regels, klaar voor import |
| `rapporten/artikelbank/import-artikelbank.py` | Importscript, draait bij Gert |
| `rapporten/artikelbank-nieuwe-leveranciers.csv` | De 54 leveranciers in één bestand |

### Rapport opnieuw publiceren

Bewerk de HTML, dan:

```bash
./rapporten/build-pdf.sh          # PDF opnieuw renderen + controle op lege pagina's
```

Voor het artifact: publiceer `rapporten/hairstuff-marktanalyse-2026.html` op
dezelfde URL hierboven (meegeven als `url`-parameter, anders ontstaat een nieuwe link).

---

## 3. Kritieke beperking van de omgeving

**Deze sandbox kan geen enkele website bereiken.** Getest en bevestigd:

```
example.com  google.com  github.com  bol.com  hairstuff.be  →  403 CONNECT
```

Alleen de zoekfunctie werkt, en die geeft samenvattingen met URL's — geen
pagina's. Gevolgen:

- hairstuff.be, de Artikelbank en concurrentwebshops zijn **niet** te bekijken.
  Dat ligt niet aan die sites; het is de proxy van deze omgeving.
- Prijzen van concurrenten en de huisstijl moeten van buiten aangeleverd worden.
- Alles wat online moet gebeuren, gaat via een sessie op **Hairstuff01** (de
  machine van Gert, 24/7 aan, kan er wel bij).

Verspil geen tijd met opnieuw proberen — meld het en werk eromheen.

---

## 4. De cijfers (peildatum 10 augustus 2026)

Uit vijf Mplus-exports, periode 1-1-2020 t/m 10-8-2026, filiaal België.
Alles narekenbaar met de scripts in `rapporten/analyse/`.

### Omzet en marge

| | |
|---|---|
| Omzet 2026 op jaarbasis | € 375.000 excl. btw |
| Omzet 2025 | € 404.920 |
| Brutomarge op actuele prijzen | **53,9 %** |
| Brutomarge gerealiseerd 2020–2026 | 49,5 % |
| Gemiddelde factuur | € 73 (was € 67 in 2020) |
| Facturen per jaar | circa 5.500 tot 6.300 |

Let op: actuele prijzen liggen mediaan **13,1 %** boven het historische
gemiddelde. Rekenen met gerealiseerde gemiddelden geeft een verouderd beeld —
daar is Gert eerder terecht over gevallen.

### Assortiment

| | |
|---|---|
| Actieve artikelnummers | 2.804 |
| Waarvan op de webshop | 2.069 |
| Met barcode | 2.627 (93,7 %) |
| Inactief met historie | 2.950 |
| Actief maar nooit verkocht | 19 |
| Actief met 5 stuks of minder | 937 |

De barcodedekking is hoog genoeg om prijsvergelijking met concurrenten te
automatiseren — de EAN is de koppelsleutel.

### Klanten en geografie

| | |
|---|---|
| Unieke klantnamen | 6.551 |
| Top 20 % klanten | **85,4 %** van de omzet |
| Top 10 klanten | 14,1 % |
| Top 12 plaatsen | 47,4 % van de omzet |
| Grootste plaats | Westmalle, 12,5 % |

Dit is een uitgesproken **regionale toonbankgroothandel**, geen e-commercebedrijf.

### De webshop

**0,9 % van de omzet.** € 23.601 van € 2.603.779 sinds 2020, en in 2026 tot
10 augustus **nul webshopfacturen**. Bevestigd door twee bestanden onafhankelijk
(facturen en orders).

> **Openstaand:** klopt dit, of worden webshoporders sinds 2026 zonder
> herkenbare verwijzing gefactureerd? Dit bepaalt de volgorde van het hele plan,
> want de vier talen en de marktplaatsplannen bouwen erop voort.

### Leveranciersconcentratie

Sens.ùs via Super Hair Brands: **31,0 %** van de omzet en **28,4 %** van de
brutowinst. Grootste enkelvoudige afhankelijkheid.

Promotiekorting op ColorGrace, MC2 en Giulietta: € 88.209 over de periode,
oftewel **€ 13.406 per jaar**. Op 10 augustus alleen al € 81,84 op een dagomzet
van € 1.169 — zeven procent.

### Eigen label

7,0 % van het volume bij **62,5 %** marge, tegen 53,0 % op al het overige.
Margeverschil 9,5 punt. Naar 20 % brengen is circa **€ 4.650 per jaar**.

### Belangrijke artikelprijzen (actueel, excl. btw)

| Artikel | Inkoop | Verkoop | Marge |
|---|---|---|---|
| Sens.ùs Giulietta 100 ml | 5,08 | 12,71 | 60,0 % |
| Sens.ùs ColorGrace 100 ml | 4,68 | 12,02 | 61,1 % |
| L'Oréal Majirel 60 ml | 7,29 | 10,40 | 29,9 % |
| Wella Koleston 60 ml | 7,48 | 11,10 | 32,6 % |
| HairStuff Oxycreme 1000 ml | 2,55 | 8,14 | 68,7 % |
| HairStuff Hairspray 500 ml | 3,60 | 10,95 | 67,1 % |
| Wella EIMI Pearl Styler 100 ml | 4,95 | 15,19 | 67,4 % |

**Het sterkste verkoopargument in het dossier:** Sens.ùs kost per milliliter
bijna drie keer minder dan Koleston (€ 0,047 tegen € 0,125). Een tube is 100 ml
tegen de prijs van 60 ml — 67 procent meer product voor ongeveer hetzelfde geld.
Die rekensom staat nergens op de site, in geen van de vier talen.

---

## 5. Openstaande punten

### Blokkeert ander werk

1. **Verifiëren of de webshop echt stilstaat** (zie hierboven). Bepaalt de
   volgorde van talen, Bol en internationale groei.
2. **Negen artikelkaarten met een omdoosprijs in het stuksveld** corrigeren.
   Goldwell TopChic staat op € 912 inkoop bij een tube van € 15,20. Vertekent
   elk margeoverzicht en blokkeert promotie van die artikelen.

### Aan te leveren door Gert

| Wat | Waarvoor |
|---|---|
| **Logo en huisstijlkleuren** | De HTML heeft bovenin een blok `HUISSTIJL` met drie merkkleuren en een logoslot. Inplakken is twee minuten. Nu staat er een neutrale koperkleur en een tijdelijk `HS`-blokje |
| **Concurrentprijzen per artikel** | Om het prijshoofdstuk hard te maken met basis- én actieprijzen. Instructie staat hieronder |
| **Orderregels uit Mplus** | Staffeldrempels op werkelijke bestelhoeveelheden; aanhechtingsgraad van eigen oxydant op kleurorders |
| **Leveranciersovereenkomsten** | Rebatestaffels, en de marktplaatsbepalingen die bepalen of Bol überhaupt mag |
| **Voorraadwaarde per artikel** | Om te weten of de 937 trage artikelen ook dood kapitaal zijn |
| **Bol Partnerplatform-tarieven** | De exacte commissie en voordeeltreden zijn alleen in zijn eigen account zichtbaar |

### Lopend

- **Artikelbank-import.** Het script staat klaar maar is nog niet gedraaid.
  Gert draait `import-artikelbank.py` op Hairstuff01 (proefdraai eerst), stuurt
  de uitvoer door, dan de koppeling afmaken voor de drie kolomindelingen.
- **Kursaal Gel Extra Forte 500 ml.** Prijs 23 % gezakt naar € 8,22 terwijl de
  inkoop steeg naar € 3,87; marge van 66,2 naar 52,9 procent. Eigen merk, dus de
  prijs is volledig een keuze. Was daar een reden voor?

---

## 6. Instructie voor een sessie op Hairstuff01

Concurrentprijzen ophalen — dit kan die machine wel:

```
Open deze webshops en noteer per product de actuele prijs incl. en excl. btw,
plus of het een actie- of basisprijs is. Zet het resultaat in een CSV met
kolommen: product | shop | prijs_incl | prijs_excl | actie_ja_nee | url | datum

Shops: haibu.nl, kapperswinkel.be, voorkappers.nl, haarshop.com,
kappersoutlet.com, beautyaswell.be, kikiskappersgroothandel.nl, myhair.nl,
knipengoshop.nl, en voor Duitsland basler-pro.de, alfastore.de, hair24.de

Producten (de high runners uit Mplus):
- Sens.ùs Giulietta 7.0 100ml, MC2 7.0 100ml, ColorGrace 6.0 100ml
- Sens.ùs Oxycreme Lux 20vol 1000ml
- Sens.ùs T@B>U Fixer 300ml, Bang Styler 400ml, After Pillow 200ml
- Wella EIMI Pearl Styler 100ml
- L'Oréal Tec Ni Art Volume Extra Full 250ml
- Sens.ùs Illumyna Nutri Repair Mask 250ml
- Sens.ùs Inblonde Deco Ultra Platinium 9 450gr
- ProCare 24*7 Alufoil 12cm x 450m
- Sibel Handschoenen Wegwerp 50st

Noteer ook per shop: verzendkosten en de drempel voor gratis verzending.
```

Artikelbank laden:

```bash
pip install requests beautifulsoup4
export AB_USER='hairstuff'
export AB_PASS='...'                      # wachtwoord is gewijzigd, vraag het opnieuw

python3 import-artikelbank.py             # proefdraai, schrijft niets
python3 import-artikelbank.py --commit    # werkelijk inladen
```

---

## 7. Brondata

De Mplus-exports zijn **niet** in de repo opgenomen: ze bevatten inkoopprijzen
en marges per artikel. Ze stonden in de uploadmap van de sessie en zijn daarmee
weg. Voor nieuwe berekeningen moeten ze opnieuw aangeleverd worden:

| Export | Wat erin staat |
|---|---|
| Artikelprestatie | Actuele verkoopprijs, actuele gemiddelde inkoopprijs, actief-vlag, webshopvlag, barcode, verkoophistorie |
| Verkoopfacturen | 37.800 facturen met klant, plaats, bedrag, datum |
| Verkooporders | Webshoporders |
| Verloop | Omzet per uur van één dag |
| BPE | Voorraadstand en inkoopprijs per stuk |

**Belangrijk bij het parsen:**

- Getalnotatie is Belgisch: punt als duizendtalscheiding, komma als decimaal.
- De artikelprestatie-export heeft meerdere regels per artikelnummer;
  ontdubbelen scheelt 0,2 % op de omzet, dus de regels zijn grotendeels echt.
- Twee bedrijfsvoertuigen (Mercedes en Audi, samen € 54.959) staan als omzet
  geboekt met 100 % marge. Eruit filteren, anders staat de marge 1,2 punt te hoog.
- Negen artikelkaarten hebben een omverpakkingsprijs in het stuksveld. Filteren
  op `inkoopprijs > 3 × verkoopprijs` vangt ze.

---

## 8. Wat er al in het rapport staat

Drie delen, elf hoofdstukken, 41 pagina's, 153 klikbare links en 70 genummerde
bronverwijzingen naar 33 bronnen.

**Deel A — Diagnose.** De cijfers, waar winst weglekt, onderscheidend vermogen.

**Deel B — Kansen.** Europese trends met marktcijfers, prijspositie tegenover
concurrenten, de vier talen, eigen merk uitbreiden, Hairstation op Bol, en 45+
nieuwe leveranciers met richtprijzen en marges plus 33 concepten.

**Deel C — Uitvoering.** Korte, middellange en lange termijn, elk met kosten per
aanpassing, opbrengst per jaar en een prioritering (P1 blokkeert ander werk,
P2 levert het meeste per euro, P3 kan wachten).

### Kernconclusies

1. Het bedrijf is gezond: 53,9 % marge, stabiele omzet, sterke regionale positie.
2. Het opruimwerk levert circa **€ 16.000 per jaar** op zonder investering, en
   betaalt daarmee alle experimenten in het plan.
3. De webshop is 0,9 % — daar ligt de grootste onbeantwoorde vraag.
4. Bol werkt alleen voor duurdere artikelen: vier head-spa-sets leveren evenveel
   op als 763 gelflessen.
5. Eigen label uitbreiden is echt maar bescheiden (€ 4.650 per jaar); de reden om
   het te doen is spreiding van de Sens.ùs-afhankelijkheid, niet de marge.

### Bewuste keuzes in de opzet

- Geen enkele verwijzing naar de eerdere Grok-analyse. Die klopte niet en Gert
  wilde hem er expliciet uit.
- Bedrijfscijfers dragen geen bronnummer (die komen uit Mplus en zijn
  narekenbaar); elke marktuitspraak wel.
- Prijzen bij leveranciers die nog niet gevoerd worden zijn **richtprijzen**,
  afgeleid van de margestructuur in de eigen boeken. Dat staat er expliciet bij.
