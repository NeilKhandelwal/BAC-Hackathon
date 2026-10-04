# Sensitive and protected land near the candidate counties

The brief asks about "proximity to sensitive areas and ecosystems." The
engine doesn't score that: the land pillar's `pct_protected` column was
never built, so land is scored on population density and county area only.
This note records the check done by hand for Grant County, WA (the
featured county), Clark County, WA, and Franklin County, NY, and a
county-level protected-land share that was built and measured but not
shipped.

**Bottom line.** None of the three reference sites has a protected-land,
tribal-land, or legal conflict that would block a 300 MW campus. Grant
County has a lot of wildlife land, but none of it is within 5 km of Quincy,
and Quincy already hosts a cluster of hyperscale data centers. The real
work is process: cultural resource surveys and, where a federal permit is
involved, tribal consultation. Clark and Franklin each have a county-scale
constraint (the Columbia River Gorge National Scenic Area, and the
Adirondack Park), but neither reaches its reference site.

## How it was checked

- **Distances** are straight-line distances from a reference point to the
  nearest polygon edge, computed in a local projection (about ±0.5 km).
  They come from live queries on 2026-10-04 against:
  - USGS PAD-US 4.1 ([feature service](https://services.arcgis.com/v01gqwM5QqNysAAi/arcgis/rest/services/PADUS_Protection_Status_by_GAP_Status_Code/FeatureServer/0))
  - Census TIGERweb 2024 tribal and county layers ([service](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS2024/MapServer))
  - USFS forest boundaries and ownership ([EDW](https://apps.fs.usda.gov/arcx/rest/services/EDW/))
  - the Adirondack Park Agency's Blue Line ([layer](https://services2.arcgis.com/8krRUWgifzA4cgL3/ArcGIS/rest/services/BluelinePolygon/FeatureServer/0))
- **Query output and scripts** are in `scratch/sensitive_land/phase1/`.
  The full report is in `phase1_report.txt`.
- **Reference points:**
  - Quincy for Grant (47.234 N, 119.852 W), the existing data center
    cluster.
  - Vancouver for Clark (45.639 N, 122.661 W). A real site would more
    likely be in unincorporated north or east county.
  - Malone for Franklin (44.848 N, 74.295 W), the county seat.
- **What's left out:** WA DNR trust land, which PAD-US lists but which is
  managed for revenue, not conservation. Slivers under 1 km² are also
  dropped.
- **County shares** (`pct_protected`) come from USGS's PAD-US 4.1 county
  summary, using GAP status 1 and 2. USGS describes those as managed
  primarily for biodiversity. See "County shares" below.

## Grant County, WA (Quincy)

Nearest features, from closest:

| Feature | Type | Manager | In Grant? | Distance from Quincy |
| --- | --- | --- | --- | --- |
| Columbia Basin Wildlife Area parcels | State wildlife area | WDFW | Yes | 5.8 km W |
| Beezley Hills | Conservation land, NGO-managed (GAP 2) | NGO | Yes | 6.1 km NE |
| BLM Wenatchee Field Office parcels | Public land, multiple use | BLM | Yes | 7.2 km NE |
| Quincy Lakes Unit, Columbia Basin Wildlife Area | State wildlife area | WDFW | Yes | 8.6 km S |
| Columbia River (Priest Rapids Project reach) | Grant PUD hydro project, FERC license P-2114 | Grant PUD | County line | 10.6 km W |
| Desert Unit | State wildlife area | WDFW | Yes | 22.6 km SE |
| Ginkgo Petrified Forest State Park | State park | WA State Parks | No (Kittitas) | 28.5 km SW |
| Okanogan-Wenatchee National Forest | National forest | USFS | No | 30.8 km W |
| Sun Lakes-Dry Falls State Park | State park | WA State Parks | Yes | 35.8 km NE |
| Columbia National Wildlife Refuge | National wildlife refuge | USFWS | Partly (rest in Adams) | 41.0 km S |
| Hanford Reach National Monument | National monument | USFWS | Partly | 54.3 km SE |
| Alpine Lakes Wilderness | Wilderness (nearest) | USFS | No | 67.3 km W |
| Colville off-reservation trust land | Tribal trust land | Colville Tribes | No | 74.7 km N |
| Colville Reservation | Federal reservation | Colville Tribes | No | 86.4 km N |
| Yakama Nation Reservation | Federal reservation | Yakama Nation | No | 90.7 km SW |
| Lake Roosevelt National Recreation Area | NPS unit (nearest) | NPS | Touches the county | 101.1 km NE |

**What the 12.8% is made of.** Grant's GAP 1-2 land totals 229,095 acres
(`scratch/sensitive_land/grant_breakdown.py`):
- Hanford Reach (69,441 acres, 54 km), the Desert Unit (54,808 acres,
  23 km), and Columbia NWR (15,358 acres, 41 km) make up 61%.
- 57,563 acres lie within 10 km of Quincy: Columbia Basin Wildlife Area
  parcels, Beezley Hills, and Quincy Lakes.
- None lies within 5 km.
- No tribal land is inside Grant County (TIGER 2024).

**Assessment.** No conflict. The wildlife areas within 10 km are nearby,
not a constraint: the existing cluster sits on the same kind of irrigated
farmland. The binding limits at Quincy are power allocation and
transmission (`research/risk.md`), not land.

## Clark County, WA

| Feature | Type | Manager | In Clark? | Distance from Vancouver |
| --- | --- | --- | --- | --- |
| Fort Vancouver National Historic Site | NPS unit | NPS | Yes | 1.2 km S |
| Shillapoo Wildlife Area | State wildlife area | WDFW | Yes | 4.1 km NW |
| Ridgefield National Wildlife Refuge | National wildlife refuge | USFWS | Yes | 13.3 km NW |
| Columbia River Gorge National Scenic Area | National scenic area | USFS and Gorge Commission | Yes (about 31 km² at the east end) | 21.6 km E |
| Battle Ground Lake State Park | State park | WA State Parks | Yes | 21.8 km NE |
| Cowlitz Reservation | Federal reservation | Cowlitz Indian Tribe | Yes (La Center area) | 23.2 km N |
| Steigerwald Lake National Wildlife Refuge | National wildlife refuge | USFWS | Yes | 26.0 km E |
| Gifford Pinchot National Forest | National forest | USFS | Yes (about 4.9 km²) | 32.6 km E |
| Mount St. Helens National Volcanic Monument | National monument | USFS | No | 56.0 km NE |

**Assessment.** A siting constraint, not a blocker.
- **Real constraint:** the Gorge Scenic Area's rules would seriously
  constrain an industrial campus at the county's east end.
- **To avoid:** the Ridgefield and Shillapoo lowlands, and the Cowlitz
  reservation near La Center.
- **Survey step:** Clark County requires an archaeological
  predetermination for many SEPA-reviewed parcels
  ([county page](https://clark.wa.gov/community-development/archaeological-review)).

## Franklin County, NY

| Feature | Type | Manager | In Franklin? | Distance from Malone |
| --- | --- | --- | --- | --- |
| Adirondack Park (Blue Line) | Park boundary; APA land-use jurisdiction inside | NYS APA and DEC | 68% of the county | 6.1 km (Malone is outside) |
| Deer River State Forest | State forest | NYSDEC | Yes | 10.3 km SW |
| Chazy Highlands Wild Forest | Forest Preserve | NYSDEC | Partly | 10.6 km SE |
| Debar Mountain Wild Forest | Forest Preserve | NYSDEC | Yes | 17.3 km S |
| Saint Regis Mohawk off-reservation trust land | Tribal trust land | Saint Regis Mohawk Tribe | Yes | 21.7 km NW |
| Saint Regis Mohawk Reservation (Akwesasne, US side) | Federal reservation | Saint Regis Mohawk Tribe | Yes | 24.8 km NW |
| McKenzie Mountain Wilderness | Wilderness (nearest) | NYSDEC | No | 53.5 km SE |
| Missisquoi National Wildlife Refuge | National wildlife refuge (nearest) | USFWS | No (Vermont) | 86.2 km E |

**Assessment.** No conflict at Malone. At county scale there are two
constraints:
- **The Adirondack Park:** about 68% of the county lies inside the Blue
  Line, where any site needs an Adirondack Park Agency permit and large
  industrial use is limited to certain land classes.
- **Akwesasne land claim:** the settlement is pending in Congress, not
  enacted. It could restore reservation status to land 20 to 30 km
  northwest of Malone.

## Tribal consultation and cultural resources

**Triggers.**
- **Federal:** [Section 106](https://www.achp.gov/protecting-historic-properties/section-106-process/introduction-section-106)
  of the National Historic Preservation Act applies to projects a federal
  agency carries out, funds, permits, licenses, or approves. A private
  campus on private land triggers it only through a federal connection,
  such as an Army Corps Section 404 permit, a BPA interconnection, federal
  funding, or work on a FERC-licensed hydro project's lands.
- **Washington:** [Executive Order 21-02](https://governor.wa.gov/sites/default/files/exe_order/eo_21-02.pdf)
  requires consultation with DAHP and affected tribes for state-funded
  projects that don't get Section 106 review.
- **New York:** the [SHPO](https://parks.ny.gov/shpo/environmental-review/)
  reviews state- or federally-involved projects under Section 14.09 of the
  State Historic Preservation Act.

**Grant County.**
- **Yakama Nation:** Quincy appears to sit inside the Yakama Nation's 1855
  ceded area, by a reading of the
  [treaty's boundary text](https://treaties.okstate.edu/treaties/treaty-with-the-yakima-1855-0698).
  That reading hasn't been checked against an official map. Ceded land
  isn't reservation land and gives no land-use authority over private
  parcels, but it makes the Yakama Nation an affected tribe in federal and
  state cultural review.
- **Wanapum:** Grant PUD describes a long relationship with the
  [Wanapum](https://www.grantpud.org/the-wanapum), dating from the
  licensing of Priest Rapids and Wanapum dams. The Wanapum Heritage Center
  is next to their ancestral village near Priest Rapids Dam, south of
  Quincy.
- **Colville:** the Confederated Tribes of the Colville Reservation are an
  expected consulting party for the mid-Columbia.
- **Where the risk sits:** irrigated upland farmland carries less
  archaeological risk than land along the Columbia, Crab Creek, or the
  coulees.

**Clark County.**
- **Cowlitz Indian Tribe:** the main consulting party; its reservation is
  in the county.
- **Chinook Indian Nation:** not federally recognized, so it can be
  invited into Section 106 review but has no right to consult.
- **Yakama ceded area:** Clark appears to be outside it.

**Franklin County.** The Saint Regis Mohawk Tribe's
[Tribal Historic Preservation Office](https://www.srmt-nsn.gov/programs/tribal-historic-preservation-office)
handles Section 106 consultation.

## County shares (built, measured, not shipped)

`etl/adapters/pad_us.py` and `etl/adapters/tribal_lands.py` compute
county shares. The measurement is in
`scratch/sensitive_land/measure.py`.

| County | GAP 1-2 (`pct_protected`) | National percentile | GAP 1-3 | Tribal land share |
| --- | --- | --- | --- | --- |
| Grant, WA | 12.8% | 89th | 23.4% | 0% |
| Clark, WA | 2.8% | 59th | 18.4% | 0.04% |
| Franklin, NY | 32.0% | 98th | 50.1% | 1.2% |
| Berkshire, MA | 18.0% | 93rd | 34.8% | 0% |

**Scored in the land pillar** (as `engine/pillars.yaml` specifies):
- Grant falls from 1st to 4th under `balanced`. Whitman WA becomes 1st,
  0.87 points ahead of Grant.
- Grant's share of random weightings that put it in the top 10 falls from
  50.5% to 14.0%.
- The other presets keep their #1: Wayne TN for `speed_to_power`, Whitman
  WA for `sustainability_first`.
- No top-10 county under that scoring has much protected or tribal land.

The column wasn't shipped because, for the featured county, the county
share disagrees with the site check: the protected land is real but isn't
at Quincy. Percentile scoring also turns a modest gap into a large one
(0.2% against 12.8% is about 89 percentile points). As a gate instead of
a score, a 25% or 50% cap leaves the top 10 unchanged and Grant passes.

**A county share is a screen, not a siting check.** A 150-acre campus can
avoid protected land inside a county, so a parcel-level check belongs in
feasibility.

## Unverified

1. That Quincy is inside the Yakama 1855 ceded area, and that Clark is
   outside it. These are readings of the treaty text, not checked against
   an official map.
2. The Wanapum's federal recognition status. Not checked against the BIA
   list.
3. Colville (Moses-Columbia) territory in Grant County. The only source is
   a school district's land acknowledgement.
4. Whether the river reach 10.6 km west of Quincy is inside the FERC
   P-2114 project boundary.
5. PAD-US labels "Lenore Game Range" and "Colockum Game Range" as USFWS
   land. They're probably WDFW land.
6. The Columbia NWR county split. It comes from PAD-US polygons only.
7. The Clark County Code chapter for archaeological review. The code site
   returned 403; the county's review process itself is confirmed.
8. The Gifford Pinchot acreage in Clark County: 4.9 km² per USFS layers
   against 0.5 km² per PAD-US.
9. Whether the Akwesasne settlement passed after its June 2026 Senate
   hearing.
10. The Quincy data center tenants and acreages, which come from search
    snippets of filings and press.
11. DEC wildlife management areas in Franklin County. PAD-US shows none
    within 50 km of Malone.
