import json
rows=json.load(open('data.json'))['rows']
E=lambda r,k: r[k] or 0

# --- corrupte kostprijsregels opsporen: kostprijs per stuk > verkoopprijs per stuk * 3
corrupt=[]
for r in rows:
    a,oe,k=E(r,'aantal'),E(r,'oe'),E(r,'kost')
    if a>0 and oe>0 and k>0:
        if (k/a) > 3*(oe/a): corrupt.append(r)
cm=sum(E(r,'oe')-E(r,'kost') for r in corrupt)
ck=sum(E(r,'kost') for r in corrupt); co=sum(E(r,'oe') for r in corrupt)
print("="*94); print("A. CORRUPTE KOSTPRIJZEN (kostprijs/stuk meer dan 3x de verkoopprijs/stuk)"); print("="*94)
print(f"  {len(corrupt)} regels | omzet excl {co:,.0f} | geboekte kostprijs {ck:,.0f} | vertekening in marge {cm:,.0f}")
for r in sorted(corrupt,key=lambda r:E(r,'oe')-E(r,'kost'))[:12]:
    a=E(r,'aantal')
    print(f"    {r['oms'][:44]:<46} nr {r['nr']:>6}  {a:>6,.0f} st  vk/st {E(r,'oe')/a:>7.2f}  kp/st {E(r,'kost')/a:>9.2f}")

clean=[r for r in rows if r not in corrupt]
def tot(rs):
    o=sum(E(r,'oe') for r in rs); k=sum(E(r,'kost') for r in rs); return o,k,o-k
o1,k1,m1=tot(rows); o2,k2,m2=tot(clean)
print(f"\n  gerapporteerd  omzet {o1:>12,.0f}  marge {m1:>12,.0f}  ({m1/o1*100:.2f} %)")
print(f"  na correctie   omzet {o2:>12,.0f}  marge {m2:>12,.0f}  ({m2/o2*100:.2f} %)")

# --- niet-productregels
NP=('PROMOTIE KORTING','Verzendkosten','Gift Card','CURSUS','ONTBREKENDE','Losse verkoop')
np=[r for r in clean if any(t.lower() in r['oms'].lower() for t in NP)]
prod=[r for r in clean if r not in np]
o3,k3,m3=tot(prod); o4,k4,m4=tot(np)
print(f"\n  waarvan niet-product (korting/verzending/cadeaubon): omzet {o4:>10,.0f}  marge {m4:>10,.0f}")
print(f"  ZUIVERE PRODUCTMARGE                                omzet {o3:>10,.0f}  marge {m3:>10,.0f}  ({m3/o3*100:.2f} %)")

print()
print("="*94); print("B. EIGEN LABEL (HairStuff / Kursaal) versus de rest"); print("="*94)
own=[r for r in prod if any(t in r['oms'].lower() for t in ('hairstuff','kursaal'))]
rest=[r for r in prod if r not in own]
oo,ok,om=tot(own); ro,rk,rm=tot(rest)
print(f"  eigen label   {len(own):>4} artikelen  omzet {oo:>11,.0f}  ({oo/o3*100:>5.1f} % van omzet)  marge {om:>10,.0f}  ({om/oo*100:.1f} %)")
print(f"  overig        {len(rest):>4} artikelen  omzet {ro:>11,.0f}  ({ro/o3*100:>5.1f} %)                marge {rm:>10,.0f}  ({rm/ro*100:.1f} %)")
print(f"\n  Top eigen-labelartikelen:")
for r in sorted(own,key=lambda r:-(E(r,'oe')-E(r,'kost')))[:10]:
    a=E(r,'aantal'); m=E(r,'oe')-E(r,'kost')
    print(f"    {r['oms'][:44]:<46}{a:>7,.0f} st  omzet {E(r,'oe'):>9,.0f}  marge {m:>9,.0f} ({m/E(r,'oe')*100:>5.1f} %)")

print()
print("="*94); print("C. ARTIKELPRODUCTIVITEIT — de staart"); print("="*94)
s=sorted(prod,key=lambda r:-E(r,'oe')); n=len(s)
cum=0; marks=[.5,.8,.9,.95]; mi=0
for i,r in enumerate(s,1):
    cum+=E(r,'oe')
    while mi<len(marks) and cum>=marks[mi]*o3:
        print(f"  {marks[mi]*100:>4.0f} % van de omzet komt van {i:>5} artikelen ({i/n*100:>4.1f} % van het assortiment)")
        mi+=1
low=[r for r in prod if E(r,'aantal')<=2]
print(f"\n  artikelen met 2 stuks of minder verkocht: {len(low):,} van {n:,} ({len(low)/n*100:.1f} %) — samen {sum(E(r,'oe') for r in low):,.0f} omzet ({sum(E(r,'oe') for r in low)/o3*100:.1f} %)")
