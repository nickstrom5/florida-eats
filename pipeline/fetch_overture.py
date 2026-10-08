"""Download the Overture Maps extracts that florida.py reads -> data/fl/

- overture_fl_bbox.parquet     every place in Florida's bounding box (name, category, address, point)
- overture_fl_sources.parquet  which datasets each Florida eating/drinking listing came from (Meta, Foursquare, ...)
- fl_shapes.json               simplified state and county outlines for the map (land only: bays and the Keys' water are cut out)
- fl_state_detail.geojson      the state outline at fuller detail, for the in-state test
- fl_counties_detail.geojson   county polygons for assigning each place to a county (not shipped)
- addresses_fl.parquet         Overture address points statewide, to place DBPR license records (they have no coordinates)

Reads the public Overture bucket over S3 with DuckDB (no account needed). Adapted from co-eats/pipeline/fetch_overture.py.
"""
import os, json, time
import duckdb
from shapely import wkb
from shapely.geometry import mapping

RELEASE = "2026-09-23.1"
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "fl")
# Florida (24.4°N–31.0°N, 80.0°W–87.6°W, Dry Tortugas to Pensacola) plus a margin for border towns
BBOX = "bbox.xmin BETWEEN -87.75 AND -79.8 AND bbox.ymin BETWEEN 24.3 AND 31.05"
EAT = "('restaurant','casual_eatery','bar','fast_food_restaurant','coffee_shop','cafe','smoothie_juice_bar','brewery','food_court')"
os.makedirs(OUT, exist_ok=True)

con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial; SET s3_region='us-west-2';")
places = f"s3://overturemaps-us-west-2/release/{RELEASE}/theme=places/type=place/*.parquet"

t = time.time()
if not os.path.exists(f"{OUT}/overture_fl_bbox.parquet"):
    con.execute(f"""
COPY (
  SELECT id, names.primary AS name, basic_category AS cat, taxonomy.primary AS tax, taxonomy.hierarchy AS hier, confidence,
         operating_status AS status, brand.names.primary AS brand, addresses[1].freeform AS street, addresses[1].locality AS city,
         addresses[1].postcode AS zip, addresses[1].region AS region, ST_Y(geometry) AS lat, ST_X(geometry) AS lon, websites[1] AS web,
         phones[1] AS phone
  FROM read_parquet('{places}', hive_partitioning=1) WHERE {BBOX}
) TO '{OUT}/overture_fl_bbox.parquet' (FORMAT PARQUET)""")
    print("places in bbox", round(time.time() - t), "s", flush=True)
if not os.path.exists(f"{OUT}/overture_fl_sources.parquet"):
    con.execute(f"""
COPY (
  SELECT id, list_transform(sources, x -> x.dataset) AS ds, list_transform(sources, x -> x.update_time) AS ut,
         list_transform(sources, x -> x.record_id) AS rid,
         len(socials) AS n_soc, len(websites) AS n_web, len(phones) AS n_ph
  FROM read_parquet('{places}', hive_partitioning=1)
  WHERE {BBOX} AND basic_category IN {EAT}
) TO '{OUT}/overture_fl_sources.parquet' (FORMAT PARQUET)""")
    print("sources", round(time.time() - t), "s", flush=True)

if not os.path.exists(f"{OUT}/fl_shapes.json"):
    areas = f"s3://overturemaps-us-west-2/release/{RELEASE}/theme=divisions/type=division_area/*.parquet"
    rows = con.execute(f"""
      SELECT subtype, names.primary AS name, ST_AsWKB(geometry) AS g
      FROM read_parquet('{areas}', hive_partitioning=1)
      WHERE country = 'US' AND region = 'US-FL' AND subtype IN ('region', 'county') AND class = 'land'
        AND bbox.xmin > -88 AND bbox.xmax < -79.5 AND bbox.ymin > 24 AND bbox.ymax < 31.2""").fetchall()

    def rings(geom, tol, min_area):
        geom = geom.simplify(tol, preserve_topology=True)
        polys = [p for p in getattr(geom, "geoms", [geom]) if p.geom_type == "Polygon" and p.area >= min_area]
        return [[[round(x, 3), round(y, 3)] for x, y in p.exterior.coords] for p in polys]

    out = {"state": None, "counties": []}
    for sub, name, g in rows:
        geom = wkb.loads(bytes(g)).buffer(0)
        if sub == "region":
            json.dump(mapping(geom.simplify(0.0005, preserve_topology=True)), open(f"{OUT}/fl_state_detail.geojson", "w"))
            # small min_area keeps the Keys (each key is a tiny polygon)
            out["state"] = [[r] for r in rings(geom, 0.002, 0.00002)]
        else:
            out["counties"].append({"name": name, "c": rings(geom, 0.004, 0.00005)})
    json.dump({name: mapping(wkb.loads(bytes(g)).buffer(0).simplify(0.0003, preserve_topology=True))
               for sub, name, g in rows if sub == "county"}, open(f"{OUT}/fl_counties_detail.geojson", "w"))
    json.dump(out, open(f"{OUT}/fl_shapes.json", "w"), separators=(",", ":"))
    print("outlines: state", len(out["state"] or []), "rings +", len(out["counties"]), "counties;", round(time.time() - t), "s", flush=True)

if not os.path.exists(f"{OUT}/addresses_fl.parquet"):
    addr = f"s3://overturemaps-us-west-2/release/{RELEASE}/theme=addresses/type=address/*.parquet"
    con.execute(f"""COPY (SELECT number, street, unit, postcode, postal_city, address_levels[1].value AS state,
      address_levels[-1].value AS muni, ST_Y(geometry) lat, ST_X(geometry) lon FROM read_parquet('{addr}', hive_partitioning=1)
      WHERE country = 'US' AND {BBOX})
      TO '{OUT}/addresses_fl.parquet' (FORMAT PARQUET)""")
    print(con.execute(f"select count(*), count(*) filter (where state='FL') from '{OUT}/addresses_fl.parquet'").fetchall(),
          round(time.time() - t), "s", flush=True)
print("done", round(time.time() - t), "s")
