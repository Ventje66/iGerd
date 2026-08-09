import csv,json,re
P='/root/.claude/uploads/7ec2cdb2-0e1d-5e09-9b48-b6e57f7fba45/50d06d1e-art09082026.csv'
def num(s):
    s=(s or '').strip()
    if s in ('','NAN'): return None
    try: return float(s.replace('.','').replace(',','.'))
    except: return None
rows=[];tot=None
rd=csv.reader(open(P,encoding='utf-8-sig'),delimiter=';')
hdr=None
for rec in rd:
    if not rec or len(rec)<13: continue
    if rec[0].startswith('A.Omschrijving'): hdr=rec; continue
    if hdr is None: continue
    oms,nr=rec[0].strip(),rec[1].strip()
    d=dict(oms=oms,nr=nr,aantal=num(rec[2]),winst=num(rec[5]),margepct=num(rec[6]),
           btw=num(rec[7]),inkp=num(rec[8]),gemprijs=num(rec[9]),
           oi=num(rec[10]),oe=num(rec[11]),inkw=num(rec[12]))
    if oms=='' and nr=='': tot=d; continue
    rows.append(d)
json.dump(rows,open('art.json','w'))
E=lambda r,k: r[k] or 0
o=sum(E(r,'oe') for r in rows); w=sum(E(r,'winst') for r in rows); iw=sum(E(r,'inkw') for r in rows)
print(f"artikelen {len(rows):,}")
print(f"som regels : omzet excl {o:>14,.2f}  inkoopwaarde {iw:>14,.2f}  winst {w:>13,.2f}  ({w/o*100:.2f} %)")
print(f"eindtotaal : omzet excl {tot['oe']:>14,.2f}  inkoopwaarde {tot['inkw']:>14,.2f}  winst {tot['winst']:>13,.2f}  ({tot['winst']/tot['oe']*100:.2f} %)")
verkocht=[r for r in rows if E(r,'aantal')>0]
print(f"\nartikelen met verkoop: {len(verkocht):,} van {len(rows):,}  ->  {len(rows)-len(verkocht):,} artikelen ({(len(rows)-len(verkocht))/len(rows)*100:.1f} %) verkochten NIETS in 6,5 jaar")
