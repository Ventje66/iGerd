import json,re
rows=json.load(open('data.json'))['rows']
E=lambda r,k: r[k] or 0
corrupt={id(r) for r in rows if E(r,'aantal')>0 and E(r,'oe')>0 and E(r,'kost')>0 and E(r,'kost')/E(r,'aantal')>3*E(r,'oe')/E(r,'aantal')}

def group(pat, exclude=None):
    hits=[r for r in rows if re.search(pat,r['oms'],re.I) and id(r) not in corrupt
          and (not exclude or not re.search(exclude,r['oms'],re.I)) and E(r,'aantal')>0]
    a=sum(E(r,'aantal') for r in hits); o=sum(E(r,'oe') for r in hits); k=sum(E(r,'kost') for r in hits)
    return dict(n=len(hits),a=a,o=o,k=k,vk=o/a if a else 0,kp=k/a if a else 0,m=(o-k)/o if o else 0)

# Grok-lijstprijzen (excl. btw) tegenover werkelijk gerealiseerde prijzen
cases=[
 ("L'Oréal Majirel 60 ml", r"majirel.*60\s*ml",  11.40, 9.58,  "Haibu"),
 ("Wella Koleston Perfect 60 ml", r"koleston.*60\s*ml", 14.20, 9.15, "band 7,85–10,45"),
 ("Indola Profession 60 ml", r"indola profession.*60\s*ml", 11.95, 5.25, "Haibu actie"),
 ("HairStuff Oxycreme 1000 ml", r"hairstuff oxycreme.*1000\s*ml", 8.14, 6.00, "Sibel/KIS typisch"),
]
print("="*104)
print("D. LIJSTPRIJS VOLGENS GROK  versus  WERKELIJK GEREALISEERDE PRIJS")
print("="*104)
print(f"{'product':<30}{'Grok zegt':>10}{'werkelijk':>11}{'afwijking':>11}{'kostprijs':>11}{'marge':>8}{'concurrent':>11}{'echt gat':>10}")
res={}
for naam,pat,grok,conc,bron in cases:
    g=group(pat); res[naam]=(g,conc)
    dev=(g['vk']-grok)/grok*100
    gap=(g['vk']-conc)/conc*100
    print(f"{naam:<30}{grok:>10.2f}{g['vk']:>11.2f}{dev:>10.1f}%{g['kp']:>11.2f}{g['m']*100:>7.1f}%{conc:>11.2f}{gap:>9.1f}%")

print()
print("="*104)
print("E. BREAK-EVEN MET DE ECHTE MARGES  (v = m/(m-d) - 1)")
print("="*104)
print(f"{'ingreep':<52}{'korting':>9}{'marge nu':>10}{'nodig volume':>14}{'oordeel':>14}")
for naam,pat,grok,conc,bron in cases[:3]:
    g,c=res[naam]
    d=(g['vk']-c)/g['vk']; m=g['m']
    if m-d<=0:
        v='onmogelijk'; oordeel='onder inkoop'
    else:
        vv=m/(m-d)-1; v=f"+{vv*100:,.0f} %"
        oordeel = 'haalbaar' if vv<0.25 else ('zwaar' if vv<0.6 else 'onhaalbaar')
    print(f"{naam+' -> concurrentprijs':<52}{d*100:>8.1f}%{m*100:>9.1f}%{v:>14}{oordeel:>14}")
    # variant: gat halveren
    tgt=g['vk']-(g['vk']-c)/2; d2=(g['vk']-tgt)/g['vk']
    vv2=m/(m-d2)-1 if m-d2>0 else None
    print(f"{'   variant: het gat halveren':<52}{d2*100:>8.1f}%{m*100:>9.1f}%{('+%.0f %%'%(vv2*100)) if vv2 else 'onmogelijk':>14}{('haalbaar' if vv2 and vv2<0.25 else 'zwaar' if vv2 and vv2<0.6 else 'onhaalbaar'):>14}")

print()
print("="*104); print("F. WAT DEZE DRIE LIJNEN EIGENLIJK VOORSTELLEN"); print("="*104)
tot_o=1777591
for naam,pat,grok,conc,bron in cases:
    g,_=res[naam]
    print(f"  {naam:<32}{g['a']:>7,.0f} st  omzet {g['o']:>9,.0f}  = {g['o']/tot_o*100:>4.1f} % van de productomzet  marge {g['o']-g['k']:>8,.0f}")
