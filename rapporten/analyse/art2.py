import json,re
rows=json.load(open('art.json')); E=lambda r,k: r[k] or 0
o=sum(E(r,'oe') for r in rows); n=len(rows)
print("="*92); print("G. DE STAART OVER 6,5 JAAR — 15.914 artikelnummers"); print("="*92)
s=sorted(rows,key=lambda r:-E(r,'oe')); cum=0; mi=0; marks=[.5,.8,.9,.95,.99]
for i,r in enumerate(s,1):
    cum+=E(r,'oe')
    while mi<len(marks) and cum>=marks[mi]*o:
        print(f"  {marks[mi]*100:>4.0f} % van de omzet komt van {i:>6,} artikelen ({i/n*100:>5.1f} % van de artikelbestanden)")
        mi+=1
for th in (0,2,5):
    lo=[r for r in rows if E(r,'aantal')<=th]
    print(f"  {th:>2} stuks of minder verkocht in 6,5 jaar: {len(lo):>6,} artikelen ({len(lo)/n*100:>5.1f} %) — samen {sum(E(r,'oe') for r in lo):>10,.0f} omzet ({sum(E(r,'oe') for r in lo)/o*100:>4.1f} %)")

print()
print("="*92); print("H. KERNPRODUCTEN — kruiscontrole tegen het margebestand"); print("="*92)
def g(pat,excl=None):
    h=[r for r in rows if re.search(pat,r['oms'],re.I) and E(r,'aantal')>0 and (not excl or not re.search(excl,r['oms'],re.I))]
    a=sum(E(r,'aantal') for r in h); oo=sum(E(r,'oe') for r in h); k=sum(E(r,'inkw') for r in h)
    return len(h),a,oo,k,(oo/a if a else 0),(k/a if a else 0),((oo-k)/oo*100 if oo else 0)
for naam,pat in [("Majirel 60ml",r"majirel.*60\s*ml"),("Koleston 60ml",r"koleston.*60\s*ml"),
                 ("HairStuff Oxycreme 1L",r"hairstuff oxycreme.*1000"),("Eigen label HairStuff/Kursaal",r"hairstuff|kursaal")]:
    c,a,oo,k,vk,kp,m=g(pat)
    print(f"  {naam:<32}{c:>4} art {a:>8,.0f} st  omzet {oo:>10,.0f}  vk/st {vk:>6.2f}  inkoop/st {kp:>6.2f}  marge {m:>5.1f} %")
own=[r for r in rows if re.search(r'hairstuff|kursaal',r['oms'],re.I)]
oo=sum(E(r,'oe') for r in own)
print(f"\n  eigen label = {oo/o*100:.1f} % van de omzet over 6,5 jaar (tegen 7,0 % in het recentere margebestand)")
