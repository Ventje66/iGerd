# Analysescripts Mplus-exports

Reproduceren van de cijfers in hoofdstuk "De werkelijke cijfers uit Mplus".
De CSV-exports zelf staan bewust NIET in deze repo — ze bevatten inkoopprijzen
en marges per artikel. Zet ze lokaal neer en pas het pad boven in elk script aan.

| Script | Wat het doet |
|---|---|
| `parse2.py` | Leest de leveranciers-margeexport, verifieert de aansluiting op alle 39 subtotalen en het eindtotaal |
| `a4.py` | Spoort corrupte kostprijsregels op, splitst eigen label van de rest, meet de staart |
| `a5.py` | Vergelijkt Grok-lijstprijzen met gerealiseerde prijzen en herberekent break-even |
| `art.py` | Leest de artikelprestatie-export en verifieert de aansluiting |
| `art2.py` | Staartanalyse en kruiscontrole van de kernproducten tegen het margebestand |

## Belangrijk bij hergebruik

- Getalnotatie is Belgisch: punt als duizendtalscheiding, komma als decimaal.
- De artikelprestatie-export bevat meerdere regels per artikelnummer; ontdubbelen
  scheelt 0,2 % op de omzet, dus de regels zijn grotendeels legitiem.
- De artikelprestatie- en slapende-artikelenexport zijn disjunct: samen vormen ze
  de volledige catalogus van 11.371 kaarten.
- Het margebestand vermeldt geen periode. Zolang die onbekend is, zijn alle
  euro-effecten niet naar een jaar te herleiden; verhoudingen en prijzen per stuk wel.
