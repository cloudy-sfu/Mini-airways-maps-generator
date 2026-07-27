import json
import logging
import os
import re
import sqlite3
import sys
from argparse import ArgumentParser

import numpy as np
import pandas as pd
from shapely import Polygon
from shapely import get_coordinates
from shapely.affinity import translate

from airports_base import get_airport_info
from coord_to_dist import location_offset, location_offset_inverse
from little_nav_map import parse_geometry
from open_street_map import get_map

# %% Start logging system.
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)

# %% Command line arguments.
arg_parser = ArgumentParser()
arg_parser.add_argument("--db_path", required=True, type=str)
arg_parser.add_argument("--icao", required=True, type=str)
arg_parser.add_argument("--min_cam_size", required=False, default=6.5, type=float)
arg_parser.add_argument("--max_cam_size", required=False, default=10.5, type=float)
arg_parser.add_argument("--vertical_resolution", required=False, default=1440, type=int)
args, _ = arg_parser.parse_known_args()

# %% Initialization.
db_path = os.path.join(args.db_path, "little_navmap_navigraph.sqlite")
icao = args.icao.upper()
os.makedirs("results", exist_ok=True)

# %% Get airport location.
with open("sql/airport.sql") as f:
    sql_airport = f.read()
c = sqlite3.connect(db_path)
airport_loc = pd.read_sql(sql_airport, c, params={"icao": icao})
c.close()
assert airport_loc.shape[0] > 0, "Cannot find airport location."
airport_loc = airport_loc.to_dict(orient="records")[0]

airport_center_lon = airport_loc["lonx"]
airport_center_lat = airport_loc["laty"]

# %% Get airspace map.
scale = 0.69  # unit: point/km
north_offset = args.max_cam_size / scale
south_offset = - north_offset
east_offset = north_offset * 16 / 9
west_offset = - east_offset
east_lon, north_lat = location_offset_inverse(
    airport_center_lon, airport_center_lat,
    east_offset, north_offset
)
west_lon, south_lat = location_offset_inverse(
    airport_center_lon, airport_center_lat,
    west_offset, south_offset
)
assert not np.isnan([west_lon, east_lon, south_lat, north_lat]).any(), \
    "Airspace exceeds latitude range 85°S -> 85°N."
background_map = get_map(
    west_lon, east_lon, south_lat, north_lat, args.vertical_resolution)

# %% Get airport name.
airport_info = get_airport_info(icao)

# %% Initialize map.
contain_airport = re.search(r"airport", airport_info['name'], re.IGNORECASE)
if contain_airport:
    airport_name = airport_info['name']
else:
    airport_name = airport_info['name'] + " Airport"
mini_airways_map = {
    "Runways": [],
    "Terrains": [],
    "RestrictedAreas": [],
    "DirectionalRestrictedAreas": [],
    "SpawnPoints": [],
    "TxtMarkers": [],
    "ImageMarkers": [],
    "MapName": f"{airport_name}, {airport_info['city']}, {airport_info['country']}",
    "BGImageB64": background_map,
    "MapSize": 1,
    "MinimumCamSize": args.min_cam_size,
    "MaximumCamSize": args.max_cam_size,
    "initialCameraOffset": {
        "x": 0,
        "y": 0
    },
    "IS1": 85,  # default values in Mini Airways level editor
    "IS2": 70,
    "IS4": 25,
    "IS3": 30,
    "OS1": 45,
    "OS2": 40,
    "OS3": 20,
    "OS4": 15,
    "NoRndGen": False,
    "EnableWeather": False
}

# %% Runways.
runway_pattern = re.compile(r'^(0[1-9]|[12]\d|3[0-6])([LCR])?$')
runway_multiplier_scale = scale / 1.617833  # unit: multiplier/km
with open("sql/runways.sql") as f:
    sql_runways = f.read()
c = sqlite3.connect(db_path)
runways = pd.read_sql(sql_runways, c, params={"airport_id": airport_loc["airport_id"]})
c.close()
runway_center_x_km, runway_center_y_km = location_offset(
    airport_center_lon,
    airport_center_lat,
    runways["lonx"],
    runways["laty"],
)
# Mini Airways map unit.
runways["x"] = runway_center_x_km * scale
runways["y"] = runway_center_y_km * scale

for i, runway in runways.iterrows():
    runway_identifier = re.search(runway_pattern, runway["sec_ident"])
    runway_identifier_side = (runway_identifier and runway_identifier.group(2)) or ""

    ma_runway = {
        "x": runway["x"],
        "y": runway["y"],
        "r": 360 - runway["heading"],
        "lr": runway_identifier_side,
        "nominalOffset": 0,
        "lengthMultiplier": np.clip(
            runway["length_km"] * runway_multiplier_scale, 1, 5),
        "id": i + 1,
        "parallelIds": [],
        "disableTOStart": not runway["pri_takeoff"],
        "disableTOEnd": not runway["sec_takeoff"],
        "disableLandStart": not runway["pri_land"],
        "disableLandEnd": not runway["sec_land"],
        "restrictTOStart": False,
        "restrictTOEnd": False,
        "restrictLandStart": False,
        "restrictLandEnd": False
    }
    mini_airways_map["Runways"].append(ma_runway)

# %% Restricted area.
with open("sql/restricted.sql") as f:
    sql_restricted_1 = f.read()
ext_dist = 0.5
text_size = 0.2
text_horizontal_bound = args.max_cam_size * 16 / 9 - 0.5
text_vertical_bound = args.max_cam_size - 0.3
restricted_type_dict = {  # See also: sql/restricted.sql
    "P": "Prohibited",
    "R": "Restricted",
    "M": "Military",
    "W": "Warning",
    "AL": "Alert",
    "DA": "Danger",
    "CN": "Caution",
}
c = sqlite3.connect(db_path)
restricted = pd.read_sql(sql_restricted_1, c, params={
    "west_lon": west_lon,
    "east_lon": east_lon,
    "south_lat": south_lat,
    "north_lat": north_lat,
})
c.close()
restricted['geometry'] = restricted['geometry'].apply(parse_geometry)
restricted_no_shift = []
for _, area in restricted.iterrows():
    vertex_coords = area['geometry']
    vertex_x_km, vertex_y_km = location_offset(
        airport_center_lon, airport_center_lat,
        vertex_coords[:, 0], vertex_coords[:, 1]
    )
    vertex_x = vertex_x_km * scale
    vertex_y = vertex_y_km * scale
    inner_shape_no_shift = Polygon(np.column_stack([vertex_x, vertex_y]))
    restricted_no_shift.append(inner_shape_no_shift)
    center = inner_shape_no_shift.centroid
    inner_shape = translate(inner_shape_no_shift, xoff=-center.x, yoff=-center.y)
    inner_path = get_coordinates(inner_shape.exterior)[:-1]
    outer_shape = inner_shape.buffer(
        distance=ext_dist,
        join_style="mitre",
        mitre_limit=1,
    )
    outer_path = get_coordinates(outer_shape.exterior)[:-1]
    ma_area = {
        "x": center.x,
        "y": center.y,
        "innerPath": [
            {"x": inner_path[i, 0], "y": inner_path[i, 1]}
            for i in range(inner_path.shape[0])
        ],
        "outerPath": [
            {"x": outer_path[i, 0], "y": outer_path[i, 1]}
            for i in range(outer_path.shape[0])
        ],
        "extDist": ext_dist,
    }
    mini_airways_map["RestrictedAreas"].append(ma_area)
    label_text = restricted_type_dict.get(area["type"], "Unidentified")
    if pd.notna(area["name"]):
        label_text += ":\n" + area["name"]
    label = {
        "x": np.clip(-text_horizontal_bound, center.x, text_horizontal_bound),
        "y": np.clip(-text_vertical_bound, center.y, text_vertical_bound),
        "r": 0,
        "text": label_text,
        "size": text_size,
    }
    mini_airways_map["TxtMarkers"].append(label)

# %% Point terrains.
obstacles_db_path = "raw/obstacles.sqlite"
if not os.path.isfile(obstacles_db_path):
    logging.error("Installation isn't completed. Please run:\n"
                  "python agg_openaip_obstacles.py")
    exit(1)
with open("sql/obstacles.sql") as f:
    sql_obstacles = f.read()
c = sqlite3.connect(obstacles_db_path)
point_obstacles = pd.read_sql(sql_obstacles, c, params={
    "west_lon": west_lon,
    "east_lon": east_lon,
    "south_lat": south_lat,
    "north_lat": north_lat,
})
c.close()
vertex_x_km, vertex_y_km = location_offset(
    airport_center_lon, airport_center_lat,
    point_obstacles["lon"], point_obstacles["lat"]
)
point_obstacles["x"] = vertex_x_km * scale
point_obstacles["y"] = vertex_y_km * scale


def create_simplex_pentagon(x, y):
    return {
        "x": x,
        "y": y,
        "innerPath": [
            {"x": 0, "y": 1},
            {"x": -0.9510565400123596, "y": 0.30901697278022766},
            {"x": -0.5877851843833923, "y": -0.8090170621871948},
            {"x": 0.5877853631973267, "y": -0.8090169429779053},
            {"x": 0.9510564804077148, "y": 0.3090171217918396}
        ],
        "outerPath": [
            {"x": 1.5399999618530273, "y": 0.5},
            {"x": 0, "y": 1.6200000047683716},
            {"x": -1.5399999618530273, "y": 0.5},
            {"x": -0.949999988079071, "y": -1.309999942779541},
            {"x": 0.949999988079071, "y": -1.309999942779541}
        ],
        "extDist": 0.5
    }


for _, object_ in point_obstacles.iterrows():
    ma_object = create_simplex_pentagon(object_["x"], object_["y"])
    mini_airways_map["Terrains"].append(ma_object)
    if pd.notna(object_["name"]):
        label = {
            "x": np.clip(-text_horizontal_bound, object_["x"], text_horizontal_bound),
            "y": np.clip(-text_vertical_bound, object_["y"], text_vertical_bound),
            "r": 0,
            "text": object_["name"],
            "size": text_size,
        }
        mini_airways_map["TxtMarkers"].append(label)

# %% Export.
cycle_path = os.path.join(args.db_path, "cycle.json")
with open(cycle_path, "r") as f:
    cycle = json.load(f)
with open(f"results/Map-{icao}-{cycle['cycle']}-{cycle['revision']}.cm1", "w") as f:
    json.dump(mini_airways_map, f)
