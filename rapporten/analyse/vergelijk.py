import json,re
from collections import defaultdict
rows=json.load(open('art2026.json')); E=lambda r,k:(r.get(k) or 0)
A=defaultdict(lambda:{'a':0.,'oe':0.,'w':0.,'ink':0.,'oms':'','prijs':None,'ik':None,'act':False,'web':False,'bc':''})
for r in rows:
    d=A[r['nr']]
    d['a']+=E(r,'aantal'); d['oe']+=E(r,'oe'); d['w']+=E(r,'winst'); d['ink']+=E(r,'inkw')
    d['oms']=r['oms']; d['act']=d['act'] or r['actief']; d['web']=d['web'] or r['webshop']
    if r['prijs']: d['prijs']=r['prijs']
    if r['gem_ink_kaart']: d['ik']=r['gem_ink_kaart']
    if r['barcode']: d['bc']=r['barcode']
A={k:v for k,v in A.items() if not re.search(r'audi|mercedes|lichte vracht',v['oms'],re.I)}

print("="*118)
print("ACTUELE PRIJS EN INKOOP tegenover het HISTORISCH GEMIDDELDE 2020-2026")
print("="*118)
print(f"{'artikel':<44}{'hist vk':>9}{'nu vk':>9}{'Δ':>7}{'hist ik':>9}{'nu ik':>9}{'hist m%':>9}{'nu m%':>8}")
pats=[('HairStuff Oxycreme 20Vol 1000ml',r'^HairStuff Oxycreme 20Vol 1000'),
      ('Kursaal Gel Extra Forte 500ml',r'^Kursaal Gel Extra Forte 500'),
      ('Hairstuff Mousse Normaal 300ml',r'^Hairstuff Mousse Normaal 300'),
      ('Hairstuff Hairspray 300ml',r'^Hairstuff Hairspray 300'),
      ('HairStuff Hairspray 500ml',r'^HairStuff Hairspray 500'),
      ('Sens.ùs ColorGrace 6.0 100ml',r'^Sens.ùs ColorGrace 6\.0 100'),
      ('Sens.ùs Giulietta 7.0 100ml',r'^Sens.ùs Giulietta 7\.0 100'),
      ('Sens.ùs MC2 7.0 100ml',r'^Sens.ùs MC2 7\.0 100'),
      ('Wella EIMI Pearl Styler 100ml',r'Wella EIMI Pearl Styler 100'),
      ('Chi Enviro Hairspray 340gr',r'Chi Enviro 54.* Hairspray Natural Hold 340'),
      ('Sens.ùs T@B>U Fixer 300ml',r'T@B>U Fixer 300'),
      ('Sens.ùs T@B>U After Pillow 200ml',r'T@B>U After Pillow 200'),
     ]
for label,p in pats:
    hits=[v for v in A.values() if re.search(p,v['oms'],re.I)]
    if not hits: print(f"  {label:<42} GEEN TREFFER"); continue
    v=max(hits,key=lambda v:v['oe'])
    hvk=v['oe']/v['a'] if v['a'] else 0; hik=v['ink']/v['a'] if v['a'] else 0
    hm=v['w']/v['oe']*100 if v['oe'] else 0
    nvk=v['prijs']; nik=v['ik']
    nm=(nvk-nik)/nvk*100 if nvk and nik else None
    d=(nvk-hvk)/hvk*100 if nvk and hvk else 0
    print(f"  {label:<42}{hvk:>9.2f}{(nvk or 0):>9.2f}{d:>+6.0f}%{hik:>9.2f}{(nik or 0):>9.2f}{hm:>8.1f}%{(nm or 0):>7.1f}%")

print()
print("="*118); print("HOE GROOT IS DE AFWIJKING OVER HET HELE ACTIEVE ASSORTIMENT?"); print("="*118)
act=[v for v in A.values() if v['act'] and v['a']>=10 and v['prijs'] and v['ik'] and v['oe']>0]
dev=[( (v['prijs'] - v['oe']/v['a'])/(v['oe']/v['a'])*100 ) for v in act]
dev.sort()
import statistics as st
print(f"  {len(act):,} actieve artikelen met >=10 verkopen, actuele prijs en inkoop bekend")
print(f"  mediane afwijking actuele prijs t.o.v. historisch gemiddelde: {st.median(dev):+.1f} %")
print(f"  25e percentiel {dev[len(dev)//4]:+.1f} %   75e percentiel {dev[3*len(dev)//4]:+.1f} %")
hm=sum(v['w'] for v in act)/sum(v['oe'] for v in act)*100
nm=sum((v['prijs']-v['ik'])*v['a'] for v in act)/sum(v['prijs']*v['a'] for v in act)*100
print(f"\n  gewogen marge historisch  : {hm:.1f} %")
print(f"  gewogen marge op actuele prijzen: {nm:.1f} %   ->  {nm-hm:+.1f} procentpunt")
