# Implementation vision: Grant County, WA

How a 300 MW data center campus in Grant County, Washington (FIPS 53025;
Quincy, Moses Lake, Ephrata) could run sustainably over 30 years. Data and
engine are frozen at tag `data-freeze-2026-10-03` (main 39b5b9f). The full
risk table is in `research/risk.md`.

Markers on outside claims: **[C]** a source confirms it, **[P]** partly
confirmed or sources disagree, **[U]** unconfirmed. Opus research agents
gathered the sources on 2026-10-03. We checked the claims the plan rests on
against their primary sources: the Grant PUD data center FAQ, the March 2025
load caps, BPA's new large single load rule, and Massachusetts Executive
Order 658. Numbers without a marker come from this repo.

## The plan in five sentences

1. Grant County has cheap power, dense fiber, an existing data center
   cluster, and low cooling demand today, but none of its existing hydro is
   available to a new 300 MW load: the utility's dam share already falls
   short of its current load, and new large loads must fund new supply.
2. So the campus starts small. It energizes a first phase behind the
   utility's queue once Quincy's transmission upgrades land in 2027 and 2029,
   and it grows to 300 MW only as new supply that the campus pays for comes
   online.
3. That supply is new solar, wind, and storage contracted through Grant PUD
   in the first decade, about 1 GW of solar to match a year's use, then firm
   clean power (pumped storage or small modular reactors) in the 2030s, so
   the campus meets Washington's 2030 greenhouse-gas-neutral and 2045
   100-percent-clean standards.
4. It uses no evaporative cooling. Closed-loop warm-water liquid cooling with
   dry coolers fits a county with high water stress and a city at its water
   right limits, and it is designed for the triple in 95 F days expected by
   2050.
5. It sites next to a food processor so its 45 to 65 C liquid-cooling return
   water can feed process heat, and it shares its tax base and hiring with a
   county where data centers already pay most of Quincy's property taxes.

**The cost headline.** Grant's cheap power belongs to existing customers. A
new campus is a new large single load, so federal power comes at BPA's New
Resources rate of about $80 to $132 per MWh, or the campus funds its own
supply. Energy then costs $196 million to $323 million a year, against the
$162 million that today's 6.61 cents/kWh implies and $226 million in Loudoun
County, VA. The engine's cost column can't see this, because it uses today's
average industrial price. Above about $92.50 per MWh, Grant costs more than
Loudoun.

## Why Grant County

Grant's rank depends on whether electricity cost is scored on its own:

- Under the seven-pillar balanced preset at the data-freeze tag, Grant ranks
  7th of 1,565 gate-passing counties (composite 61.4, robustness 0.65).
- With cost as an eighth pillar, weighted 0.15 (PR #28), Grant ranks 1st
  (composite 63.7, robustness 1.00).

The team picked Grant because of that second ranking. A site-selection lead
pays the power bill, and a ranking that ignores it put Berkshire County, MA,
at 18.19 cents/kWh, first. The cost pillar uses today's average industrial
price, which a new load won't get (see the cost headline above).

From `python -m engine explain --conditions engine/conditions/balanced.yaml
--fips 53025`. The per-column percentiles are the same under both presets:

| Factor | Grant County | Engine percentile (higher is better) |
| --- | --- | --- |
| Industrial power price | 6.61 cents/kWh | 77th |
| Fiber share of locations | 0.99 | 95th |
| Clean generating capacity within 100 km | 16,193 MW | 100th |
| Existing data centers in the table | 3 | 99th |
| Cooling degree days | 655 today, 1,177 by 2050 | 74th |
| Days above 95 F | 14.5 today, 35.9 by 2050 | 30th |
| Water stress (WRI Aqueduct) | 3.62 of 5, flat to 2050 | 16th |
| Heat wave loss rate | 97.35 | 3rd |
| Wildfire loss rate | 86.93 | 13th |

The weak points are water, heat, and wildfire. The plan answers the first two
directly. The engine excludes Grant under evaporative cooling because water
stress is above the gate.

From `research/impact.md` and team research: the campus draws about 2,444,000
MWh a year (300 MW IT, load factor 0.8, dry-cooling PUE 1.163). That is about
279 average MW (aMW). At today's 6.61 cents/kWh it would cost about $162
million a year, $64 million less than Loudoun County, VA. That is a floor; the
cost headline above gives the range a new load faces.

## Phases

| | Years 0 to 5 (2027 to 2031) | Years 5 to 15 (2032 to 2041) | Years 15 to 30 (2042 to 2056) |
| --- | --- | --- | --- |
| Load | First phase energized after Quincy transmission upgrades, sized to Grant PUD's allocation | Grow toward 300 MW as funded supply and transmission arrive | 300 MW, refreshed hardware |
| Power | Join the queue. Fund new solar plus storage through Grant PUD, about 2 to 2.5 years from contract to operation | About 1 GW of solar for annual matching, plus wind and storage. Add firm clean supply: pumped storage from 2031 to 2032, small modular reactors in the 2030s | 100 percent clean under CETA from 2045. Move from annual to hourly matching |
| Cooling | Closed-loop direct-to-chip liquid cooling with dry coolers. No evaporative cooling | Raise supply water temperatures with each hardware generation | Refit heat rejection for about 36 days a year above 95 F |
| Heat | Choose a site next to a food processor. Pipe stubs in at construction | First heat export with heat pumps | Expand if the heat buyer grows |
| Community | Start construction before July 1, 2035 to qualify for the state sales tax exemption. Local hiring | Tax base for schools and city. Biofuel or battery backup instead of diesel | Exemption expires July 1, 2048. Plan for full tax exposure |

## Site and power

This is the plan's biggest risk.

**The existing cluster.** Microsoft built Quincy's first data center in 2006.
**[C]** ([Spokesman-Review](https://www.spokesman.com/stories/2026/jul/26/where-agriculture-meets-technology-inside-the-smal/))
Operators now include Microsoft, Sabey, Vantage, H5, CyrusOne, NTT Data, and
Oath. **[C]** (same source) Grant PUD serves 8 data center operators, who used
about 280 aMW in 2025, about 37 percent of the county's 757 aMW system load.
**[C]** ([Grant PUD FAQ, 2026-08-28](https://www.grantpud.org/blog/data-center-faqs))

**The hydro is spoken for.** Grant PUD owns Priest Rapids (950 MW) and Wanapum
(1,221.6 MW) dams. **[C]** ([Grant PUD](https://www.grantpud.org/generation))
It holds rights to 63.31 percent of their output, and the dams average about
1,000 MW. **[C]** ([FAQ](https://www.grantpud.org/blog/data-center-faqs))
Grant's share is therefore about 633 aMW, less than its 757 aMW load today.
Data centers are served with "available excess hydro generation along with
Grant PUD's other power resources and market purchases as needed." **[C]**
(FAQ) A new campus's 279 aMW would be about 44 percent of Grant's hydro
share. None of it is spare.

**The queue and the caps.** About 800 MW of large-load requests sit in Grant
PUD's queue. Large users pay for new generation, transmission, and
distribution, and "service cannot always be provided as quickly as customers
or developers may prefer." **[C]** (FAQ) In March 2025, Grant PUD capped how
much each data center can grow. The binding limit is transmission into
Quincy: one project finishes in 2027, and a new high-capacity line from
Wanapum Dam to Quincy in 2029. **[C]**
([Columbia Basin Herald](https://columbiabasinherald.com/news/2025/mar/31/grant-pud-places-limits-on-electrical-demand-from-data-centers/))
For 2027, staff propose new rate classes for high-density compute, with a
12.5 percent average increase for that tier and increases expected each year
through 2036. **[C]**
([APPA](https://www.publicpower.org/periodical/article/grant-pud-commissioners-considering-proposal-create-new-electric-rate-classes-data-centers))
That proposal is not adopted.

**BPA is not cheap for this load.** Under the Northwest Power Act, a new load
that grows by 10 aMW or more in 12 months is a new large single load. It must
be served with BPA power at the New Resources rate or with dedicated
non-federal resources. **[C]**
([BPA fact sheet](https://www.bpa.gov/-/media/Aep/about/publications/fact-sheets/fs-202011-New-Large-Single-Load.pdf))
The NR-26 energy rate runs about $80 to $132 per MWh, before transmission.
**[C]**
([BPA rate schedules](https://bpa.gov/-/media/Aep/rates-tariff/bp-26/Final-Proposal/Appendix-DFinal-Proposal-Power-Rate-Schedules-and-GRSPsBP26A01AP01.pdf))
At that rate the campus would pay $196 million to $323 million a year for
energy. The $162 million figure above assumes today's average industrial
price, which existing hydro customers get. Treat it as a floor.

**Where new clean supply comes from.**

- Grant PUD is already contracting new solar and storage. Royal Slope (260 MW
  solar plus 260 MW of 4-hour storage, 20-year contracts from 2028, solar at
  $65 to $75 per MWh) was approved in October 2025. **[C]**
  ([Grant PUD packet](https://www.grantpud.org/block/documents/68e984086e515-2025-10-14-presentation-packet.pdf),
  [Clearway](https://www.clearwayenergygroup.com/press-releases/clearway-signs-power-purchase-agreement-and-energy-storage-agreement-totaling-520-mw-with-public-utility-district-of-grant-county/))
  Quincy Solar (120 MW) broke ground in August 2026 for late 2027. **[C]**
  ([Invenergy](https://wwww.invenergy.com/news/invenergy-and-grant-county-public-utility-district-celebrate-their-first-solar-project-to-break-ground-in-grant-county))
- At Royal Slope's expected 27 percent capacity factor **[C]**
  ([Grant PUD packet](https://www.grantpud.org/block/documents/68e984086e515-2025-10-14-presentation-packet.pdf)),
  matching the campus's annual use takes about 1,030 MW of solar. That is
  four Royal Slopes. Solar alone doesn't cover nights or winter, so annual
  matching still leans on the grid hour by hour.
- Firm clean options arrive in the 2030s. Goldendale pumped storage (1.2 GW,
  Klickitat County) holds a 40-year FERC license and plans operation in 2031
  to 2032. **[C]**
  ([Rye Development](https://ryedevelopment.com/federal-energy-regulatory-commission-issues-40-year-license-to-the-goldendale-energy-storage-project.html))
  Grant PUD is exploring X-energy small modular reactors and says it needs
  new capacity "somewhere in the 2030 range." **[C]**
  ([Grant PUD](https://www.grantpud.org/nuclear)) Whether any of that output
  could serve a third-party campus is unconfirmed. **[U]**
- Regional transmission is slow. BPA executives described major transmission
  builds as "a 15-year type of project." **[P]**
  ([interview, undated](https://newprojectmedia.com/interview-bonneville-power-administration-executives-discuss-new-projects-being-connected-to-grid-in-next-two-years/))

**Carbon over 30 years.** Washington's Clean Energy Transformation Act
applies to Grant PUD. **[C]**
([RCW 19.405.020](https://app.leg.wa.gov/RCW/default.aspx?cite=19.405.020))
Retail sales must be greenhouse gas neutral by January 1, 2030, with up to 20
percent met by alternative compliance. **[C]**
([RCW 19.405.040](https://app.leg.wa.gov/RCW/default.aspx?cite=19.405.040))
Renewable and non-emitting power must supply all retail sales by January 1,
2045, with no alternative compliance. **[C]**
([RCW 19.405.050](https://app.leg.wa.gov/RCW/default.aspx?cite=19.405.050))
Unspecified imported power also carries a cap-and-invest allowance cost from
the first ton. **[C]**
([RCW 70A.65.080](https://app.leg.wa.gov/RCW/default.aspx?cite=70A.65.080))

So the campus's emissions fall as the law forces the supply clean:

- **Before new supply arrives:** 236,000 to 700,390 tonnes CO2 a year,
  between BPA's balancing-authority rate (212 lb/MWh) and the Northwest
  regional average (632 lb/MWh). Loudoun is 675,455 t. The 0 t "PUD hydro"
  case doesn't apply to a new load.
- **2030 to 2044:** the utility's sales are greenhouse gas neutral, up to 20
  percent through offsets and unbundled credits. The campus's own funded
  solar and storage cover most of its annual use.
- **From 2045:** 100 percent renewable or non-emitting by law.

No sourced year-by-year intensity path exists for this supply. Any 30-year
total that holds today's rate is an upper bound.

One note on e8's figures. eGRID lists the Grant PUD balancing authority at
4.13 TWh of generation, which would make the campus 59 percent of it. Grant
PUD's own figures put the dams' average at about 1,000 MW (about 8.8 TWh), and
eGRID assigns Priest Rapids to BPA. The 44 percent of Grant's hydro share used
here comes from the utility's own numbers.

## Cooling and water

**No evaporative cooling.** The City of Quincy told a state advisory group in
October 2025 that it "is at its water right limits," with nitrate
contamination that has closed wells. **[C]**
([Columbia River Policy Advisory Group](https://www.ezview.wa.gov/Portals/_1962/Documents/CRPAG/Oct2025meetingum.pdf))
Quincy's industrial water reuse utility opened in 2021 at a cost of $31
million, paid by Microsoft, and as of 2022 served only Microsoft's campus.
**[C]**
([EPA case study](https://19january2025snapshot.epa.gov/waterreuse/water-reuse-case-study-quincy-washington))
A new campus can't count on city water. Dry cooling uses about 27.8 million
gallons a year for humidification (`research/impact.md`), against 210 million
for an evaporative design here.

**Liquid cooling makes dry coolers work.** ASHRAE's 2021 guidelines class
liquid cooling by the facility's supply water temperature. W32 and W40
typically run "without chillers in most locations." W45 and above typically
run without chillers, though "some locations may not be suitable for
drycoolers." **[C]**
([ASHRAE reference card](https://www.ashrae.org/file%20library/technical%20resources/bookstore/supplemental%20files/therm-gdlns-5th-r-e-refcard.pdf))
One vendor's rack for current Nvidia GB200 systems accepts inlet water up to
45 C and returns up to 65 C. **[C]**
([QCT](https://blog.qct.io/wp-content/uploads/2025/04/QCT-Qoolrack-Stand-Alone_Advanced-Liquid-Cooling-for-NVIDIA-GB200-NVL72-Systems.pdf))
A preprint finds dry coolers work at a 41.7 C fluid temperature at 12 US
sites at design conditions, except Phoenix, Las Vegas, and Tucson. **[P]**
([Mokkapati and Das, not peer reviewed](https://engrxiv.org/preprint/download/7795/12658/10948))

**Free-cooling hours.** We found no published economizer-hour figure for
Quincy. **[U]** Published figures depend on the method:

- The Green Grid finds 75 percent of North America can use air-side
  economizers every hour of a typical year under ASHRAE's A2 allowable range,
  with short periods up to 35 C. **[C]**
  ([Green Grid WP46](https://datacenters.lbl.gov/sites/default/files/WP46UpdatedAirsideFreeCoolingMapsTheImpactofASHRAE2011AllowableRanges.pdf))
- A stricter model of 925 US locations finds outdoor air inside the A1
  allowable envelope only 21.5 percent of the time on average. **[C]**
  ([Chen and Wemhoff 2023](https://par.nsf.gov/servlets/purl/10435467))

Our assumption, not a sourced figure: with W40 liquid cooling, dry coolers
reject heat without chillers on all but the hottest days. Quincy's dry air
helps.

**What changes by 2050.** Days above 95 F (35 C) rise from 14.5 to 35.9. On
those days, outside air is within a few degrees of a W40 supply temperature,
so the campus needs trim chillers or a small adiabatic assist for about five
weeks a year. That is our analysis. A 2026 study finds hours that limit
direct air cooling have risen since 1980 and keep rising to mid-century.
**[C]** ([Karamperidou et al.](https://www.nature.com/articles/s41598-026-56926-3))
Wildfire smoke is a second reason to avoid direct outside-air cooling. That
is our inference from the county's wildfire risk, not a sourced finding.

## Heat reuse

**What makes it work.** Heat reuse needs warm enough heat, a nearby buyer,
and a buyer who wants it year-round.

- Air-cooled exhaust is close to ambient temperature, which makes reuse
  "difficult and often impossible." Liquid cooling yields heat at 45 to 70 C.
  **[C]**
  ([ICEF roadmap 2025](https://icef.go.jp/wp-content/themes/icef_new/pdf/roadmap/2025/09_CHAPTER%20%E2%85%A1%20%E2%80%93%204.%20HEAT%20REUSE.pdf))
- Heat must be used close to where it's made, and the US has little district
  heating. **[C]** (same source;
  [Bisnow](https://www.bisnow.com/news/national/data-center/recycling-heat-from-data-centers-mostly-hot-air-118334))
- Working examples are in northern Europe. Meta's Odense data center recovers
  215,000 MWh a year with about 45 MW of heat pumps and heats more than 12,000
  homes. **[C]**
  ([Ramboll](https://www.ramboll.com/projects/energy/meta-surplus-heat-to-district-heating))
  Microsoft and Fortum plan to use about 75 percent of waste heat a year in
  Finland, because summer demand is low. **[C]**
  ([Microsoft](https://news.microsoft.com/europe/2022/03/17/microsoft-announces-intent-to-build-a-new-datacenter-region-in-finland-accelerating-sustainable-digital-transformation-and-enabling-large-scale-carbon-free-district-heating/))

**In Grant County.** There is no district heating and no data center heat
reuse project, real or proposed. **[P]** (absence of evidence) One analysis
found no existing heat user within about 1.2 miles of the Quincy data
centers. **[P]**
([Post Alley](https://www.postalley.org/2026/08/17/heating-up-could-datacenter-heat-be-an-asset/))
The engine's `heat_sink_score` is only a proxy.

The real candidates are food processors, which use heat all year, unlike
homes:

- Simplot is building a 420,000 sq ft plant in Moses Lake with 150 new jobs.
  **[C]**
  ([Source One](https://www.yoursourceone.com/columbia_basin/simplot-building-420-000-square-foot-plant-in-moses-lake/article_9c3a4c0e-84db-11ef-96a4-a74905752e67.html))
- Lamb Weston has a potato plant in Quincy. **[P]**
- Food processors use 57 percent of Quincy's city water. **[C]**
  ([WWD](https://www.wwdmag.com/wastewater-treatment/microsoft-funds-quincy-data-center-wastewater-treatment-plant))

We found no published figure for how much heat these plants use, or at what
temperature. **[U]**

The plan: put the campus next to a processor and bring the 45 to 65 C return
water to it, lifted with heat pumps where needed, as at Odense. Without
co-location, there's no credible heat buyer.

## Community and workforce

Grant County is growing, not declining. Its population rose 8.5 percent from
2020 to 2026, and Quincy's rose 13.5 percent. **[C]**
([Washington OFM](https://ofm.wa.gov/sites/default/files/public/dataresearch/pop/april1/ofm_april1_population_final.pdf))
The economic brief found that distressed places tend to gain least. Grant is
the opposite case: a county that has gained a great deal from data centers.

- Seven of the county's top 10 taxpayers are data centers. Their assessed
  value rose from $313 million in 2006 to $6.1 billion in 2025. **[C]**
  ([Washington DOR workgroup](https://dor.wa.gov/sites/default/files/2025-10/DataCenterWorkgroup_AdoptedFindings10_2025.pdf))
- Quincy's city levy rate fell about 70 percent from 2006 to 2025. **[C]**
  (same source)
- Data centers make up about 54 percent of the Quincy School District's local
  tax base. **[P]**
  ([KOMO](https://komonews.com/news/local/quincys-microsoft-data-center-boom-prompts-new-school-library-hospital-police-station-transformation-police-station-fire-public-works-buildings-aquatic-center))
- Quincy's poverty rate fell from 29.4 percent in 2012 to 13.1 percent in
  2023. **[C]**
  ([KUOW](https://www.kuow.org/stories/washington-s-hydropower-has-created-a-data-center-boom-some-are-concerned-about-its-future))

**Jobs.** About 25 to 40 operators per 100 MW is an industry benchmark,
cited secondhand. **[P]**
([Latitude Media](https://www.latitudemedia.com/news/data-center-jobs-arent-at-servers-theyre-in-energy/))
That implies 75 to 120 permanent jobs at 300 MW. Data centers have created
about 900 direct jobs in Quincy. **[C]**
([DOR](https://dor.wa.gov/sites/default/files/2025-10/DataCenterWorkgroup_AdoptedFindings10_2025.pdf))
Each building runs with fewer than 50 technicians. **[C]**
([KUOW](https://www.kuow.org/stories/washington-s-hydropower-has-created-a-data-center-boom-some-are-concerned-about-its-future))
Construction is larger and temporary: Microsoft expects more than 2,470 jobs
at peak across its current Washington build. **[C]**
([Microsoft](https://local.microsoft.com/wp-content/uploads/2025/10/Microsoft-datacenters-in-Washington.pdf))

**The state sales tax exemption.** A Grant County project very likely
qualifies under
[RCW 82.08.986](https://app.leg.wa.gov/RCW/default.aspx?cite=82.08.986)
**[C]**:

- It must be in a rural county, which Grant is.
- It needs at least 20,000 sq ft of server space.
- Construction must start by July 1, 2035.
- Within six years it must create at least 35 family-wage jobs, paying at
  least 125 percent of per capita personal income, with health insurance.
- The exemption expires July 1, 2048.
- Since July 1, 2026, it covers only original servers, not replacements.
  **[C]** ([ESSB 6231](https://app.leg.wa.gov/billsummary?BillNumber=6231&Year=2026))

So buildings started after 2035, and every hardware refresh, pay full sales
tax.

**What pushback has been about.**

- **Diesel generators:** permits to run backup generators were appealed in
  2010. Every new Quincy data center now needs a health impact assessment.
  **[C]** ([Ecology](https://ecology.wa.gov/air-climate/air-quality/data-centers))
  The plan uses renewable diesel or batteries for backup.
- **Power rates:** Grant PUD's April 2026 increases were 3.3 percent for
  residential customers and 9.1 to 11.1 percent for large and industrial
  classes. **[C]**
  ([Source One](https://www.yoursourceone.com/columbia_basin/grant-pud-rate-increase-takes-effect-april-1-core-customers-see-modest-hike/article_8dd5bec7-50c6-41f6-88a8-5ee3122c2b0a.html))
  The campus pays for its own supply, so residents don't.
- **Water:** we found no public dispute over data center water rights. **[U]**

## Embodied carbon

We didn't model embodied carbon for this campus. What's within reach:

- Concrete is the largest share. **[P]** AWS replaced 40 percent of cement
  with slag in trial batches and cut the mix's embodied carbon by more than 30
  percent. **[C]**
  ([Amazon](https://aboutamazon.com/news/sustainability/aws-decarbonizing-construction-data-centers))
- Electric arc furnace steel carries about half, and as little as one fifth,
  of the embodied carbon of blast-furnace steel. **[C]** (same source) Electric
  arc furnaces made 71.8 percent of US steel in 2024. **[C]**
  ([Argus](https://argusmedia.com/en/news-and-insights/latest-market-news/2523501-viewpoint-us-eaf-growth-fuels-prime-scrap-demand))
- Microsoft's hybrid cross-laminated timber data centers are estimated to cut
  embodied carbon 35 percent against steel construction. **[C]**
  ([Data Center Frontier](https://datacenterfrontier.com/design/article/55241410/microsoft-employs-wood-products-to-help-decarbonize-new-data-center-construction))
- The federal Buy Clean initiative ended in January 2025. **[C]**
  ([Canary Media](https://www.canarymedia.com/articles/policy-regulation/trump-rescinds-federal-program-to-boost-low-carbon-building-materials))

The plan specifies slag or other cement substitutes, electric arc furnace
steel, and environmental product declarations for both.

## What could go wrong with this vision

`research/risk.md` has the full risk table. Three risks are specific to this
plan:

1. **Power arrives late or costs more.** The phases assume the 2027 and 2029
   transmission projects finish on time, the queue moves, and new solar plus
   storage keeps coming at about $65 to $75 per MWh. If any slips, the campus
   sits at its first phase for years, or buys at BPA's $80 to $132 per MWh.
2. **Heat outruns the cooling design.** Days above 95 F more than double by
   2050, and the county's heat wave risk is already among the worst 3
   percent nationally. Dry coolers sized for today lose margin. The design must leave
   room for trim cooling without water.
3. **The heat buyer doesn't materialize.** Heat reuse depends on co-locating
   with a food processor willing to sign a long contract. Without that, the
   campus's heat is wasted like that of every other Quincy data center.

## Why not Berkshire County, MA

Berkshire County ranked first under the balanced preset before the team added
an electricity-cost pillar. Research on its best site, the former General
Electric works in Pittsfield, found it can't host 300 MW:

- **The site is too small.** The William Stanley Business Park is 52 acres,
  owned by the Pittsfield Economic Development Authority. **[C]**
  ([MassDevelopment](https://www.massdevelopment.com/news/a-52-acre-innovation-district-in-pittsfield-is-being-built-at-the-former-ge-site))
  Its largest parcel is 16.5 acres, and part of that is going to housing.
  **[C]**
  ([pittsfield.com](https://pittsfield.com/story/81179/PEDA-Site-9-Preparation-Member-Retirement.html))
- **Digging is restricted.** A recorded restriction on part of the site
  prohibits groundwater extraction and most excavation. **[C]**
  ([The Beat](https://thebeatnews.org/BeatTeam/?p=7939))
- **Part of the park is in a flood zone.** **[P]**
- **Power is expensive.** Energy at 18.19 cents/kWh would cost about $435
  million a year, against $162 million in Grant County.
- **State conditions on large projects.** Since Executive Order 658
  (September 8, 2026), a Massachusetts data center above 25 MW needs a
  community benefits agreement and new clean electricity to match its annual
  use, or alternative compliance payments. **[C]**
  ([Pierce Atwood](https://www.pierceatwood.com/alerts/governor-healey-issues-executive-order-establishing-new-requirements-data-centers))

At most, Pittsfield could host a small phased facility.

## Could not confirm

- Size thresholds and prices for Grant PUD's proposed 2027 high-density
  compute rates.
- Whether any small modular reactor output could serve a third-party campus.
- A published free-cooling hour figure for Quincy.
- Heat demand and temperature at Grant County food processors, and whether
  Lamb Weston's Quincy plant still operates.
- A sourced conversion from cooling degree days to lost free-cooling hours.
- The undated BPA interview figures (24 GW of load requests, 15-year
  transmission).
