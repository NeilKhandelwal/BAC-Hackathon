import json, urllib.parse, urllib.request, sys
from pyproj import CRS, Transformer
from shapely.geometry import Point
from shapely.ops import transform
import near
U="https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Hydro/MapServer/1/query"
def get(p):
    return json.load(urllib.request.urlopen(urllib.request.Request(U, data=urllib.parse.urlencode(p).encode()), timeout=180))
k, r = sys.argv[1], sys.argv[2]
s = near.SITES[k]
tq = Transformer.from_crs(4326, CRS.from_proj4(f"+proj=aeqd +lat_0={s['lat']} +lon_0={s['lon']} +datum=WGS84 +units=m"), always_xy=True).transform
d = get(dict(geometry=f"{s['lon']},{s['lat']}", geometryType="esriGeometryPoint", inSR=4326, distance=r, units="esriSRUnit_Kilometer", where="NAME IS NOT NULL AND AREAWATER > 500000", outFields="NAME,AREAWATER", returnGeometry="true", outSR=4326, f="json"))
best = {}
for f in d.get("features", []):
    g = near.esri_to_shape(f["geometry"])
    if g is None: continue
    n = f["attributes"]["NAME"]
    dist = transform(tq, g).distance(Point(0,0))/1000
    best[n] = min(best.get(n, 1e9), dist)
for n, v in sorted(best.items(), key=lambda kv: kv[1])[:15]:
    print(f"{v:6.1f} km  {n}")
print(d.get("exceededTransferLimit"))
