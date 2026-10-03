"""Build the seed opposition-outcome label table from FracTracker plus hand-coded cases.

Inputs: data/raw/fractracker/ft_all.csv and ft_wins.csv (run etl/fetch_fractracker.py first).
Output: data/processed/opposition_seed_labels.csv

Status mapping and reason keywords are heuristic. Any field ending in '?' was
inferred by keyword or regex, not verified by a person. See
research/opposition_labels.md for the caveats.
"""
import csv, re, math
COLS=['project_name','developer','state','county','city','announced_date','outcome_date','status','reasons','source_url']
ft=list(csv.DictReader(open('data/raw/fractracker/ft_all.csv')))
wins=list(csv.DictReader(open('data/raw/fractracker/ft_wins.csv')))
MON={m:i+1 for i,m in enumerate(['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'])}
def find_date(t):
    t=t or ''
    m=re.search(r'\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b',t)
    if m:
        y=int(m.group(3)); y=y+2000 if y<100 else y
        return f"{y:04d}-{int(m.group(1)):02d}-{int(m.group(2)):02d}?"
    m=re.search(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(?:(\d{1,2}),?\s+)?(20\d\d)\b',t,re.I)
    if m:
        mo=MON[m.group(1)[:3].lower()]
        return f"{m.group(3)}-{mo:02d}"+(f"-{int(m.group(2)):02d}" if m.group(2) else '')+'?'
    m=re.search(r'\bin\s+(\d{1,2})/(20\d\d)\b',t)
    if m: return f"{m.group(2)}-{int(m.group(1)):02d}?"
    return ''
KW=[('water',r'\bwater|aquifer|\bwells?\b|drought'),('noise',r'nois|decibel|\bhum\b|sound'),
    ('electricity_rates',r'\brates?\b|bills?\b|ratepayer|electric(ity)? cost|utility cost'),
    ('grid_strain',r'\bgrid\b|transmission|substation|power line|energy use|energy consumption'),
    ('farmland',r'farm|agricultur'),('rural_character',r'rural|character|scenic|viewshed|height'),
    ('secrecy',r'\bnda|non-disclosure|secre|confidential|transparen|shell (company|llc)|code ?name|pseudonym'),
    ('tax_abatement',r'abatement|tax (break|waiver|exemption|incentive)|incentive'),
    ('air_quality',r'air (quality|permit)|turbine|generator|emission|pollut|gas plant|gas-fired'),
    ('property_values',r'property value'),('traffic',r'traffic'),('light',r'\blight pollution|lighting'),
    ('wetlands_wildlife',r'wetland|wildlife|habitat|forest|endangered|conservation'),('historic',r'historic|battlefield'),
    ('zoning_process',r'rezon|zoning|annex')]
def reasons(t):
    t=(t or '').lower(); out=[k+'?' for k,p in KW if re.search(p,t)]
    return ';'.join(out)
def map_status(ftstatus,text,success=''):
    s=(success or '').lower(); t=(text or '').lower()
    t2=re.sub(r'(water|groundwater)\s+withdrawals?','',t)
    if 'withdr' in s or (ftstatus in ('Cancelled','Suspended') and ('withdr' in t2 or 'pulled' in t2)): return 'withdrawn'
    if 'ordinance' in s or 'zoning reform' in s or 'protective' in s: return 'moratorium'
    if s.startswith('delayed') or 'political reversal' in s: return 'delayed'
    if s.startswith('blocked') or 'denied' in s or 'denial' in s or 'rejection' in s: return 'cancelled'
    if ftstatus=='Cancelled': return 'cancelled'
    if ftstatus=='Suspended': return 'moratorium?' if 'moratori' in t else 'delayed'
    if ftstatus in ('Approved/Permitted/Under construction','Operating','Expanding'): return 'approved'
    return ftstatus.lower()+'?'
def dist(a,b):
    try: return math.hypot(float(a['lat'])-float(b['lat']),(float(a['long'])-float(b['long']))*0.8)*111
    except: return 999
rows={}
# 1. FracTracker main table
for x in ft:
    st=x['status']; push=x['community_pushback'].lower()=='yes'
    if not (st in('Cancelled','Suspended') or (push and st in('Approved/Permitted/Under construction','Operating','Expanding'))): continue
    name=x['facility_name'].strip()
    if name.startswith('http'): name=f"{x['city']} data center (unnamed)?"
    text=' '.join([x['advocacy_information'],x['other_info'],x['nda']])
    dev=x['operator_name'].strip() or (x['tenant'].strip()+'?' if x['tenant'].strip() else '')
    r=dict(project_name=name,developer=dev,state=x['state'],county=x['county'].strip(),city=x['city'].strip(),
        announced_date='',outcome_date=find_date(text),status=map_status(st,text),reasons=reasons(text+(' secrecy' if x['nda'].strip().lower().startswith('yes') else '')),
        source_url=(x['info_source_1'] or x['info_source_2']).strip(),_ft=x,_label='FT_all')
    rows[x['facility_id']]=r
# 2. FracTracker "Victories" layer, merged onto nearest main-table record
for w in wins:
    text=' '.join([w['narrative'],w['type_of_success'],w['notes']])
    best=min(ft,key=lambda x:dist(x,w)); d=dist(best,w)
    base=rows.get(best['facility_id']) if d<1.5 else None
    r=dict(project_name=w['project'].strip(),developer=(base or {}).get('developer',''),state=w['state'],county=w['county'].strip(),
        city=w['city'].strip(),announced_date='',outcome_date=find_date(text) or (base or {}).get('outcome_date',''),
        status=map_status(w['status'],text,w['type_of_success']),reasons=reasons(text+' '+((base or {}).get('_ft',{}) or {}).get('advocacy_information','')+' '+((base or {}).get('_ft',{}) or {}).get('other_info','')),
        source_url=(w['link1'] or w['link2']).strip(),_label='FT_wins')
    key=best['facility_id'] if base else 'win_'+w['win_id']
    rows[key]=r
# 3. Hand-coded overrides and additions (reasons as stated in the cited source; no ? unless inferred)
H=[
 # project_name, developer, state, county, city, announced, outcome, status, reasons, url, match_regex_for_existing_row
 ('Project Range','Tract','AZ','Maricopa','Buckeye/Goodyear','2023-12?','2024-04-18','withdrawn','height_visual;noise;grid_strain;water','https://www.abc15.com/news/business/14-billion-west-valley-data-center-project-request-withdrawn-after-cities-push-back',None),
 ('Harper Road Technology Park (Project Harper)','Diode Ventures','MO','Cass','Peculiar','2024?','2024-09?','cancelled','noise;light;health;wetlands_wildlife;property_values;grid_strain;secrecy','https://en.wikipedia.org/wiki/Opposition_to_AI_data_centers',r'Harper'),
 ('Provident Realty Advisors data center (Brassie Golf Club)','Provident Realty Advisors','IN','Porter','Chesterton','2024?','2024?','withdrawn','noise;grid_strain;water;proximity_to_homes;air_quality;property_values','https://en.wikipedia.org/wiki/Opposition_to_AI_data_centers',r'Provident'),
 ('Roundhouse Digital Infrastructure data center','Roundhouse Digital Infrastructure','OR','Hood River','Cascade Locks','2022?','2023-07','cancelled','secrecy?;water?','https://www.datacenterwatch.org/report',r'Roundhouse'),
 ('WUSF 5 Rock Creek East','WUSF 5 Rock Creek East?','TX','Tarrant','Fort Worth','2024?','2024-09','delayed','traffic;light;grid_strain;water;noise;tax_abatement','https://en.wikipedia.org/wiki/Opposition_to_AI_data_centers',None),
 ('GI Partners Santa Clara data center','GI Partners','CA','Santa Clara','Santa Clara','2024?','2025?','delayed','','https://en.wikipedia.org/wiki/Opposition_to_AI_data_centers',None),
 ('DC Blox Richmond data center','DC Blox','VA','Richmond city','Richmond','2024?','2024?','withdrawn','noise;grid_strain','https://www.datacenterwatch.org/report',None),
 ('Headwaters data center (Catlett Station)','Headwaters Site Development','VA','Fauquier','Catlett','2020?','2024?','withdrawn','water;grid_strain;noise;historic','https://en.wikipedia.org/wiki/Opposition_to_AI_data_centers',r'Catlett Station|Headwaters'),
 ('Culpeper Acquisitions technology campus','Culpeper Acquisitions LLC','VA','Culpeper','Culpeper?','2024?','2024-06-12','delayed','','https://en.wikipedia.org/wiki/Opposition_to_AI_data_centers',None),
 ('Province Group Powhatan Technology Park','Province Group','VA','Powhatan','Midlothian','2025?','2025-10','approved','','https://en.wikipedia.org/wiki/Opposition_to_AI_data_centers',r'Province Group @Powhatan'),
 ('Amazon Warrenton data center','Amazon','VA','Fauquier','Warrenton','2021?','2023-02 (approved); later voided','delayed','secrecy;historic?;rural_character?;noise?','https://en.wikipedia.org/wiki/Opposition_to_AI_data_centers',r'Warrenton Amazon'),
 ('Bolingbroke Technology Campus','undisclosed (Ingram?)','GA','Monroe','Bolingbroke','2025-05','2025-08-05','cancelled','noise;wetlands_wildlife;rural_character','https://www.13wmaz.com/article/news/local/forsyth-monroe/im-so-grateful-monroe-county-commissioners-unanimously-reject-6-billion-data-center-proposal-community/93-737f9c3b-893f-4dab-adf5-e81a4daee173',r'Bolingbroke'),
 ('Project Flo','Google (Deep Meadow Ventures LLC)','IN','Marion','Indianapolis (Franklin Township)','2025?','2025-09?','withdrawn','electricity_rates;grid_strain;water?;secrecy','https://www.carbon-direct.com/insights/why-ai-data-centers-are-being-blocked',r'Project Flo'),
 ('Balico MegaCampus','Balico','VA','Pittsylvania','Chatham','2024?','2025?','withdrawn','air_quality;health;secrecy','https://www.carbon-direct.com/insights/why-ai-data-centers-are-being-blocked',r'Balico'),
 ('Project Lincoln','Western Hospitality Partners','KY','Oldham','La Grange','2025?','2025-07','cancelled','','https://heatmap.news/politics/data-center-cancellations-2025',r'Project Lincoln: OC Data Center$'),
 ('Talen Energy Montour County rezoning','Talen Energy','PA','Montour','Washingtonville','2025?','2026-02','cancelled','electricity_rates;wetlands_wildlife','https://pgjonline.com/news/2026/february/pennsylvania-county-rejects-rezoning-for-gas-powered-data-center-project',r'Talen Energy Montour'),
 ('Dulles Cloud South','unknown','VA','Prince William','Catharpin','2025?','2026-07','cancelled','','https://www.newsfromthestates.com/node/416392',r'Dulles Cloud South'),
 ('Project Tango','unknown','FL','Palm Beach','Loxahatchee','2025?','2026-07','cancelled','','https://therealdeal.com/miami/2026/07/17/palm-beach-county-rejects-data-center-proposal/',r'Project Tango'),
 ('Project Delta','unknown','NC','Stokes','Walnut Cove','2026?','2026-08','delayed','','https://www.wfae.org/2026-08-14/planning-board-again-recommends-denial-of-stokes-data-center',r'Project Delta'),
 ('Pollard data center rezoning','unknown','SC','McCormick','McCormick?','2026?','2026-09','approved','','https://www.wrdw.com/2026/09/11/mccormick-county-council-approves-data-center-rezoning-while-tempers-flare/',None),
]
for h in H:
    keys=[k for k,v in rows.items() if h[10] and re.search(h[10],v['project_name'],re.I) and v['state']==h[2]]
    for k in keys: del rows[k]
    rows['hand_'+h[0]]=dict(zip(COLS,h[:10]),_label='hand')

DROP={('FT_wins','Tract West Valley Data Hub'),('FT_wins','Goodyear Data Center'),('FT_wins','Rock Creek Data Center'),('FT_wins','Culpeper Data Center'),
      ('FT_wins','Warrenton Data Center'),('FT_wins','Powhatan County Data Center'),('FT_wins','Talen Energy Data Center Campus'),('FT_wins','DC Blox Data Center'),
      ('FT_wins','Bowers Avenue Data Center'),('FT_all','Prince William Digital Gateway'),('FT_all','Amazon King George Data Center')}
rows={k:v for k,v in rows.items() if (v['_label'],v['project_name']) not in DROP and v['project_name']}
FIX={'GI Partners Santa Clara data center':dict(project_name='GI Partners data center, 2805 Bowers Ave',outcome_date='2024?',status='approved',reasons='data_center_concentration;water;grid_strain',source_url='https://www.svvoice.com/council-approves-data-center-in-spite-of-planning-commission-objection/'),
     'Province Group Powhatan Technology Park':dict(reasons='noise;traffic;wetlands_wildlife?',outcome_date='2025-10'),
     'Culpeper Acquisitions technology campus':dict(city='Brandy Station',reasons='rural_character;historic',source_url='https://www.datacenterdynamics.com/en/news/county-planners-recommend-denial-of-brandy-station-data-c'),
     'DC Blox Richmond data center':dict(county='Henrico?',outcome_date='2024-11',reasons='noise;height_visual;proximity_to_homes;grid_strain?',source_url='https://www.datacenterdynamics.com/en/news/proposals-for-two-data-center-projects-in-richmond-virgin'),
     'Tract Buckeye Technology Park':dict(status='approved?',outcome_date='2024-08?',developer='Tract'),
     'Amazon Warrenton data center':dict(source_url='https://www.fauquiernow.com/news/oscar-winner-robert-duvall-attends-warrenton-town-council-meeting-t'),
}
for v in rows.values():
    if v['project_name'] in FIX: v.update(FIX[v['project_name']])
out=sorted(rows.values(),key=lambda r:(r['_label']!='hand',r['state'],r['county'],r['project_name']))
with open('data/processed/opposition_seed_labels.csv','w',newline='') as fh:
    w=csv.DictWriter(fh,fieldnames=COLS+['label_source'],extrasaction='ignore'); w.writeheader()
    for r in out: r['label_source']=r['_label']; w.writerow(r)
import collections
print(len(out)); print(collections.Counter(r['status'] for r in out)); print(collections.Counter(r['_label'] for r in out))
print('county filled',sum(1 for r in out if r['county']),'reasons filled',sum(1 for r in out if r['reasons']),'outcome_date',sum(1 for r in out if r['outcome_date']),'developer',sum(1 for r in out if r['developer']))
