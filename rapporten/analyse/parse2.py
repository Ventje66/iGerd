import csv, json, re
PATH='/root/.claude/uploads/7ec2cdb2-0e1d-5e09-9b48-b6e57f7fba45/3210a7e1-levmargins09082026.csv'
def num(s):
    s=(s or '').strip().replace('\xa0','')
    if s in ('','NAN'): return None
    s=s.replace('.','').replace(',','.')
    try: return float(s)
    except: return None

rows=[]; grand=None; cur=None
with open(PATH, encoding='utf-8-sig') as fh:
    for rec in csv.reader(fh, delimiter=';'):
        if len(rec)<11: continue
        rec=[c.strip() for c in rec]
        lev=rec[0]
        if lev in ('','Leverancier') or lev.startswith('Tijdstip geëxporteerd'): continue
        if lev=='Eind totaal':
            grand=dict(aantal=num(rec[3]),oe=num(rec[5]),kost=num(rec[6]),marge=num(rec[8])); continue
        if lev=='Totaal leverancier': continue          # subtotalen zelf herberekenen
        if not re.match(r'^\d+\.\s', lev): continue      # alleen echte leveranciersregels
        cur=lev
        rows.append(dict(lev=cur, oms=rec[1], nr=rec[2], aantal=num(rec[3]),
                         oi=num(rec[4]), oe=num(rec[5]), kost=num(rec[6]),
                         marge=num(rec[8]), margepct=num(rec[9])))
json.dump({'rows':rows,'grand':grand}, open('data.json','w'))
so=sum(r['oe'] or 0 for r in rows); sk=sum(r['kost'] or 0 for r in rows)
print(f"artikelregels {len(rows)} | leveranciers {len({r['lev'] for r in rows})}")
print(f"som regels : omzet excl {so:>13,.2f}  kostprijs {sk:>13,.2f}  marge {so-sk:>13,.2f}  ({(so-sk)/so*100:.2f} %)")
g=grand
print(f"eindtotaal : omzet excl {g['oe']:>13,.2f}  kostprijs {g['kost']:>13,.2f}  marge {g['marge']:>13,.2f}  ({g['marge']/g['oe']*100:.2f} %)")
print(f"verschil   : {so-g['oe']:+.2f} / {sk-g['kost']:+.2f}  -> sluit aan")
