"""Find PAD-US 4.1 and TIGER AIANNH features near reference points.

Computes geodesic-ish distance (local azimuthal equidistant projection) from the
reference point to each polygon, and whether the polygon intersects the county.
"""
import json
import sys
import urllib.parse
import urllib.request
from collections import defaultdict

from pyproj import CRS, Transformer
from shapely.geometry import Point, Polygon, MultiPolygon, shape
from shapely.ops import transform, unary_union

PADUS = ("https://services.arcgis.com/v01gqwM5QqNysAAi/arcgis/rest/services/"
         "PADUS_Protection_Status_by_GAP_Status_Code/FeatureServer/0/query")
TIGER = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS2024/MapServer/{}/query"

SITES = {
    "grant": dict(lon=-119.852, lat=47.234, geoid="53025"),
    "clark": dict(lon=-122.661, lat=45.639, geoid="53011"),
    "franklin": dict(lon=-74.295, lat=44.848, geoid="36033"),
}


def get(url, params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)


def esri_to_shape(g):
    rings = g.get("rings")
    if not rings:
        return None
    # Ring orientation: outer rings clockwise in Esri. Simple approach:
    # build polygons from each ring and combine with symmetric difference
    # handling holes by orientation.
    from shapely.geometry import LinearRing
    outers, holes = [], []
    for r in rings:
        if len(r) < 4:
            continue
        lr = LinearRing(r)
        (holes if lr.is_ccw else outers).append(Polygon(r))
    if not outers:
        outers, holes = holes, []
    geom = unary_union([p.buffer(0) for p in outers])
    if holes:
        geom = geom.difference(unary_union([h.buffer(0) for h in holes]))
    return geom


def query_all(url, base):
    feats = []
    offset = 0
    while True:
        p = dict(base)
        if "tigerweb" not in url:
            p["resultOffset"] = offset
            p["resultRecordCount"] = 1000
        d = get(url, p)
        if "error" in d:
            raise RuntimeError(d["error"])
        fs = d.get("features", [])
        feats.extend(fs)
        if not d.get("exceededTransferLimit") or not fs or "tigerweb" in url:
            if d.get("exceededTransferLimit"): print("WARN transfer limit", url)
            break
        offset += len(fs)
    return feats


def county_geom(geoid):
    d = get(TIGER.format(82), dict(where=f"GEOID='{geoid}'", outFields="NAME,GEOID",
                                   returnGeometry="true", outSR=4326, f="json"))
    return esri_to_shape(d["features"][0]["geometry"])


def main(site_key, radius_km, mode):
    s = SITES[site_key]
    aeqd = CRS.from_proj4(f"+proj=aeqd +lat_0={s['lat']} +lon_0={s['lon']} +datum=WGS84 +units=m")
    fwd = Transformer.from_crs(4326, aeqd, always_xy=True).transform
    pt = Point(0, 0)
    cty = transform(fwd, county_geom(s["geoid"]))
    base = dict(geometry=f"{s['lon']},{s['lat']}", geometryType="esriGeometryPoint",
                inSR=4326, spatialRel="esriSpatialRelIntersects", distance=radius_km,
                units="esriSRUnit_Kilometer", returnGeometry="true", outSR=4326,
                maxAllowableOffset=0.0003, f="json")
    rows = []
    if mode == "padus":
        import os; base["where"] = os.environ.get('WHERE', "MngTp_Desc IN ('Federal','State','American Indian Lands','Joint','Regional Agency Special District')")
        base["outFields"] = "Category,Unit_Nm,MngTp_Desc,MngNm_Desc,DesTp_Desc,GAP_Sts,GIS_Acres"
        feats = query_all(PADUS, base)
        keyf = lambda a: (a["Unit_Nm"], a["MngNm_Desc"], a["DesTp_Desc"], a["Category"])
    else:
        feats = []
        for lyr in (36, 38, 40):
            b = dict(base, where="1=1", outFields="NAME,BASENAME,GEOID,AIANNH,AREALAND")
            for f in query_all(TIGER.format(lyr), b):
                f["attributes"]["_layer"] = {36: "Fed reservation", 38: "Off-res trust land", 40: "State reservation"}[lyr]
                feats.append(f)
        keyf = lambda a: (a["NAME"], a["_layer"], a["GEOID"], "")
    groups = defaultdict(lambda: dict(dist=1e12, acres=0.0, in_cty_km2=0.0, n=0))
    for f in feats:
        g = esri_to_shape(f["geometry"]) if f.get("geometry") else None
        if g is None:
            continue
        gp = transform(fwd, g)
        if not gp.is_valid:
            gp = gp.buffer(0)
        a = f["attributes"]
        k = keyf(a)
        gr = groups[k]
        dd = gp.distance(pt)
        if dd < gr["dist"]:
            import math
            from shapely.ops import nearest_points
            q = nearest_points(pt, gp)[1]
            b = (math.degrees(math.atan2(q.x, q.y)) + 360) % 360
            gr["brg"] = "inside" if dd == 0 else ["N","NE","E","SE","S","SW","W","NW"][int((b+22.5)//45) % 8]
        gr["dist"] = min(gr["dist"], dd)
        gr["acres"] += a.get("GIS_Acres") or (a.get("AREALAND") or 0) / 4046.86
        gr["in_cty_km2"] += gp.intersection(cty).area / 1e6
        gr["area_km2"] = gr.get("area_km2", 0) + gp.area / 1e6
        gr["n"] += 1
    out = sorted(groups.items(), key=lambda kv: kv[1]["dist"])
    for k, v in out:
        print(f"{v['dist']/1000:7.1f} km {v.get('brg',''):>6} | inCty {v['in_cty_km2']:9.2f}/{v['area_km2']:9.2f} km2 | {v['acres']:11.0f} ac | n={v['n']:3d} | " + " | ".join(str(x) for x in k))


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]), sys.argv[3])
