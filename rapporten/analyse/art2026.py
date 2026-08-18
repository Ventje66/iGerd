import csv,json,re
csv.field_size_limit(10**7)
P='/root/.claude/uploads/7ec2cdb2-0e1d-5e09-9b48-b6e57f7fba45/9f8a2b87-art10082026.csv'
def num(s):
    s=(s or '').strip()
    if s in ('','NAN'): return None
    try: return float(s.replace('.','').replace(',','.'))
    except: return None
def ja(s): return (s or '').strip().upper() in ('JA','J','TRUE','1','WAAR')

rows=[]; tot=None; hdr=False
for rec in csv.reader(open(P,encoding='utf-8-sig'),delimiter=';'):
    if len(rec)<43: continue
    if rec[0].startswith('A.Omschrijving'): hdr=True; continue
    if not hdr: continue
    d=dict(oms=rec[0].strip(), nr=rec[1].strip(), barcode=rec[2].strip(),
           prijs=num(rec[3]), spec=num(rec[4]), actief=ja(rec[5]),
           gem_ink_kaart=num(rec[12]), webshop=ja(rec[18]),
           aantal=num(rec[28]), winst=num(rec[31]), margepct=num(rec[32]),
           btw=num(rec[33]), gem_ink=num(rec[34]), gem_prijs=num(rec[35]),
           oi=num(rec[36]), oe=num(rec[37]), inkw=num(rec[38]))
    if d['oms']=='' and d['nr']=='': tot=d; continue
    rows.append(d)
json.dump(rows,open('art2026.json','w'))
E=lambda r,k:(r.get(k) or 0)
o=sum(E(r,'oe') for r in rows); w=sum(E(r,'winst') for r in rows)
print(f"regels: {len(rows):,}  unieke nummers: {len({r['nr'] for r in rows}):,}")
print(f"som   : omzet excl {o:>14,.2f}  winst {w:>13,.2f}  ({w/o*100:.2f} %)")
print(f"totaal: omzet excl {tot['oe']:>14,.2f}  winst {tot['winst']:>13,.2f}  ({tot['winst']/tot['oe']*100:.2f} %)")
print(f"verschil: {o-tot['oe']:+.2f}")
act=[r for r in rows if r['actief']]
web=[r for r in rows if r['webshop']]
bar=[r for r in rows if r['barcode']]
print(f"\nACTIEF      : {len({r['nr'] for r in act}):>6,} van {len({r['nr'] for r in rows}):,} artikelnummers")
print(f"OP WEBSHOP  : {len({r['nr'] for r in web}):>6,}")
print(f"MET BARCODE : {len({r['nr'] for r in bar}):>6,}  ({len({r['nr'] for r in bar})/len({r['nr'] for r in rows})*100:.1f} %)")
print(f"MET PRIJS   : {len({r['nr'] for r in rows if r['prijs']}):>6,}")
