import json, urllib.parse, urllib.request
from pyproj import CRS, Transformer
from shapely.geometry import Point
from shapely.ops import transform
import near
def get(url, p):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, data=urllib.parse.urlencode(p).encode()), timeout=180))
d = get("https://services2.arcgis.com/8krRUWgifzA4cgL3/ArcGIS/rest/services/BluelinePolygon/FeatureServer/0/query", dict(where="1=1", outFields="*", returnGeometry="true", outSR=4326, f="json"))
print(len(d["features"]), d["features"][0]["attributes"])
from shapely.ops import unary_union
blue = unary_union([near.esri_to_shape(f["geometry"]) for f in d["features"]])
s = near.SITES["franklin"]
aea = CRS.from_proj4("+proj=aea +lat_1=40 +lat_2=46 +lat_0=43 +lon_0=-75 +datum=WGS84 +units=m")
aeqd = CRS.from_proj4(f"+proj=aeqd +lat_0={s['lat']} +lon_0={s['lon']} +datum=WGS84 +units=m")
ta = Transformer.from_crs(4326, aea, always_xy=True).transform
tq = Transformer.from_crs(4326, aeqd, always_xy=True).transform
cty = near.county_geom("36033")
ca, ba = transform(ta, cty), transform(ta, blue)
print("county km2", ca.area/1e6, "inside blue km2", ca.intersection(ba).area/1e6, "share", ca.intersection(ba).area/ca.area)
print("Malone inside blue?", ba.contains(transform(ta, Point(s['lon'], s['lat']))))
print("dist Malone to blue line km", transform(tq, blue).distance(Point(0,0))/1000)
