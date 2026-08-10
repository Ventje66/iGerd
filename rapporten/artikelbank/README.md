# Artikelbank — nieuwe leveranciers en producten

105 regels in elf categorieën, klaar om in de online Artikelbank te laden:
leveranciers, nicheproducten met Bol-marge, en concepten met klantgroepen en diensten.

| Bestand | Regels | Wat |
|---|---|---|
| `01-kleur.csv` | 10 | Italiaanse kleurhuizen als margealternatief |
| `02-scalp-en-bond.csv` | 7 | K18, epres, Neofollics, System 4, Cutrin |
| `03-verzorging.csv` | 8 | Vegan, Scandinavisch en indie |
| `04-barber.csv` | 7 | Reuzel, Morfose, Proraso en verder |
| `05-getextureerd-haar.csv` | 7 | Krul en kroes, plus twee distributeurs |
| `06-apparatuur.csv` | 8 | Head spa, scharen, drogers, tondeuses |
| `07-verbruik-en-duurzaam.csv` | 3 | Plantaardig verbruik, Belgische productie |
| `08-private-label.csv` | 3 | Contractproducenten BE en PL |
| `09-inkoopkanaal.csv` | 1 | Sinelco, voor de inkoopprijs op basisartikelen |
| `10-nicheproducten-bol.csv` | 18 | Nicheproducten met uitgerekende Bol-marge |
| `11-concepten-en-diensten.csv` | 33 | Concepten, klantgroepen en diensten |

Samen 105 regels. De leveranciers staan ook in één bestand:
`../artikelbank-nieuwe-leveranciers.csv` (54 regels).

Formaat: puntkomma-gescheiden, UTF-8 met BOM, komma als decimaalteken.

**Leveranciersbestanden (01 t/m 09)** — Categorie, Leverancier, Land, Website,
Voorbeeldproduct, Inhoud, Indicatieve inkoop excl, Indicatieve salonprijs excl,
Marge %, Bol geschikt, Opmerking, Marktbron.

**Nicheproducten (10)** — Categorie, Product, Indicatieve inkoop excl, Bol prijs
incl, Commissie %, Verzendkosten, Bol omzet excl, Netto per verkoop, Marge %,
Verkopen voor EUR 1000, Bol geschikt, Leverancier-URL, Marktbron.

**Concepten en diensten (11)** — Groep, Nr, Concept, Wat het is, Kleinste test,
Kosten test, Uitsluitsel na, Marktbron.

Elke regel draagt waar mogelijk een `Marktbron`: de URL van het onderzoek of de
publicatie die de keuze onderbouwt. `Website` en `Leverancier-URL` wijzen naar de
site van de leverancier zelf.

## Inladen

`import-artikelbank.py` doet het werk. Draaien op een machine die
hairstuff.be kan bereiken — vanuit de analyse-omgeving lukt dat niet, die mag
geen enkele website benaderen.

```bash
pip install requests beautifulsoup4

export AB_USER='hairstuff'
export AB_PASS='...'            # niet in een bestand zetten

python3 import-artikelbank.py            # proefdraai, schrijft niets
python3 import-artikelbank.py --dump     # alleen tonen hoe de bank werkt
python3 import-artikelbank.py --commit   # werkelijk inladen
python3 import-artikelbank.py --commit --alleen Barber
```

Het script logt in (basisauthenticatie of inlogformulier), zoekt zelf uit hoe
de Artikelbank data aanneemt en gebruikt de eerste weg die werkt:

1. een REST-ingang onder `/wp-json/`
2. een CSV-uploadveld op de artikelbankpagina
3. een gewoon toevoegformulier, rij voor rij

**Standaard is het een proefdraai.** Het toont de koppeling van kolommen aan
formuliervelden en de eerste drie records zoals ze verstuurd zouden worden.
Controleer die koppeling voordat je `--commit` gebruikt.

## Status in plaats van live

Waar het formulier een veld voor status, herkomst of concept kent, vult het
script dat automatisch: `status = kandidaat`, `herkomst = marktanalyse 2026`,
`actief = 0`. Zo verschijnen deze artikelen niet op de webshop — het zijn
kandidaten om te bespreken met een leverancier, geen gevoerde artikelen.

De prijzen zijn richtprijzen, geen offertes. Overschrijf ze zodra de echte
prijslijst binnen is.

## Als er geen invoerweg blijkt te zijn

Dan is de Artikelbank alleen-lezen en wordt hij gevuld vanuit de webshop of
Mplus. Het script zegt dat dan met zoveel woorden. Er zijn twee uitwegen:

- **de bron aanvullen** — de nieuwe artikelen als concept in de webshop of in
  Mplus zetten, dan stromen ze vanzelf door;
- **de bank uitbreiden** — records toelaten die geen webshopartikel zijn, met
  een veld `status` (kandidaat / in onderhandeling / gevoerd) en `herkomst`.

Die tweede is de bedoeling: een artikelbank die alleen de webshop spiegelt kan
per definitie niets nieuws bevatten.
