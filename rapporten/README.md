# Rapporten

## Hairstuff.be — Marktanalyse en groeiplan 2026

| Bestand | Wat |
|---|---|
| `hairstuff-marktanalyse-2026.html` | Het rapport. Zelfstandige HTML, licht/donker-thema, eigen print-stylesheet |
| `Hairstuff-Marktanalyse-2026.pdf` | 30 pagina's A4 |
| `build-pdf.sh` | Rendert de PDF opnieuw na een wijziging in de HTML |
| `analyse/` | Scripts waarmee alle Mplus-cijfers narekenbaar zijn |

### Opzet

Drie delen, elk met een eigen functie.

**Deel A — Diagnose.** Wat de eigen cijfers zeggen: omzet en marge, waar winst weglekt,
en welk onderscheidend vermogen er al is.

**Deel B — Kansen.** Europese markttrends, prijspositie tegenover concurrenten, de vier
talen op de webshop, uitbreiding van het eigen merk, een Bol-winkel onder de naam
Hairstation, en nieuwe artikelen voor het assortiment.

**Deel C — Uitvoering.** Korte, middellange en lange termijn, elk met de kosten van de
aanpassing, de opbrengst per jaar en een prioritering van het werk dat ervoor nodig is.

### Kerncijfers

Uit de Mplus-exports van 9 augustus 2026, periode januari 2020 tot augustus 2026:

| | |
|---|---|
| Handelsomzet | € 386.354 per jaar |
| Brutowinst | € 174.257 per jaar (45,1 %) |
| Grootste leverancier | Sens.ùs, 31,0 % van de omzet en 28,4 % van de brutowinst |
| Eigen label | 7,0 % van de omzet, marge 59,2 % tegen 44,0 % op de rest |
| Catalogus | 11.371 artikelkaarten, waarvan 5.634 zonder één verkoop in 6,5 jaar |

Het opruimwerk in Deel C levert € 16.120 per jaar op tegen vrijwel geen kosten — meer dan
de eigen-labelambitie waar € 20.000 tot € 40.000 in moet.

### Huisstijl

Bovenin de HTML staat een blok `HUISSTIJL` met drie merkkleuren en een logoslot. Vervang
de hexcodes door die uit het WooCommerce-thema en zet het logo in de masthead; de rest van
het rapport neemt dat automatisch over. Tot die tijd staat er een neutrale koperkleur en
een tijdelijk `HS`-blokje.

### Bronnen en verificatie

Alle bedrijfscijfers komen uit de Mplus-exports en zijn na te rekenen met de scripts in
`analyse/`. De CSV-exports zelf staan bewust niet in deze repo: ze bevatten inkoopprijzen
en marges per artikel. Alle marktgegevens hebben een genummerde bronvermelding met URL
onderaan het rapport.

Waar een aanname is gedaan — bijvoorbeeld 15 % commissie in de Bol-berekeningen — staat
dat er expliciet bij, zodat de som met eigen tarieven te herhalen is.

### Wat nog ontbreekt

- Logo en huisstijlkleuren
- Actuele concurrentprijzen per artikel, met onderscheid tussen basis- en actieprijs
- Orderregels uit Mplus, voor staffeldrempels en de aanhechtingsgraad van eigen oxydant
- Leveranciersovereenkomsten, voor rebatestaffels en marktplaatsbepalingen
- Voorraadwaarde per artikel, om te bepalen of de dode artikelkaarten ook dood kapitaal zijn
