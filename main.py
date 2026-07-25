import json
import logging
import os
import re
import sqlite3
import sys
from argparse import ArgumentParser

import numpy as np
import pandas as pd

from airports_base import get_airport_info
from coord_to_dist import location_offset, location_offset_inverse
from open_street_map import get_map
from little_nav_map import parse_geometry
from shapely.geometry import Polygon
from shapely import get_coordinates

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
mini_airways_map = {
    "Runways": [],
    "Terrains": [],
    "RestrictedAreas": [],
    "DirectionalRestrictedAreas": [],
    "SpawnPoints": [],
    "TxtMarkers": [],
    "ImageMarkers": [],
    "MapName": f"{airport_info['name']} Airport, {airport_info['city']}, "
               f"{airport_info['country']}",
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
runways = pd.read_sql(sql_runways, c, params={"airport_id": airport_loc["airport_id"]})
for i, runway in runways.iterrows():
    runway_center_x_km, runway_center_y_km = location_offset(
        airport_center_lon,
        airport_center_lat,
        runway["lonx"],
        runway["laty"],
    )

    # Mini Airways map unit.
    runway_center_x = runway_center_x_km * scale
    runway_center_y = runway_center_y_km * scale

    runway_identifier = re.search(runway_pattern, runway["sec_ident"])
    runway_identifier_side = (runway_identifier and runway_identifier.group(2)) or ""

    ma_runway = {
        "x": runway_center_x,
        "y": runway_center_y,
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
restricted = pd.read_sql(sql_restricted_1, c, params={
    "west_lon": west_lon,
    "east_lon": east_lon,
    "south_lat": south_lat,
    "north_lat": north_lat,
})
restricted['geometry'] = restricted['geometry'].apply(parse_geometry)
for _, area in restricted.iterrows():
    vertex_coords = area['geometry']
    vertex_x_km, vertex_y_km = location_offset(
        airport_center_lon, airport_center_lat,
        vertex_coords[:, 0], vertex_coords[:, 1]
    )
    vertex_x = vertex_x_km * scale
    vertex_y = vertex_y_km * scale
    center_x = np.mean(vertex_x)
    center_y = np.mean(vertex_y)
    vertex_x -= center_x
    vertex_y -= center_y
    inner_shape = Polygon(np.column_stack([vertex_x, vertex_y]))
    outer_shape = inner_shape.buffer(
        distance=ext_dist,
        join_style="mitre",
        mitre_limit=1,
    )
    outer_path = get_coordinates(outer_shape.exterior)[:-1]
    ma_area = {
        "x": center_x,
        "y": center_y,
        "innerPath": [
            {"x": vertex_x[i], "y": vertex_y[i]}
            for i in range(vertex_coords.shape[0])
        ],
        "outerPath": [
            {"x": outer_path[i, 0], "y": outer_path[i, 1]}
            for i in range(outer_path.shape[0])
        ],
        "extDist": ext_dist,
    }
    mini_airways_map["RestrictedAreas"].append(ma_area)
    label = {
        "x": np.clip(-text_horizontal_bound, center_x, text_horizontal_bound),
        "y": np.clip(-text_vertical_bound, center_y, text_vertical_bound),
        "r": 0,
        "text": f"{restricted_type_dict.get(area["type"], "Unidentified")}:\n"
                f"{area["name"]}",
        "size": text_size,
    }
    mini_airways_map["TxtMarkers"].append(label)

# %% Export.
cycle_path = os.path.join(args.db_path, "cycle.json")
with open(cycle_path, "r") as f:
    cycle = json.load(f)
with open(f"results/Map-{icao}-{cycle['cycle']}-{cycle['revision']}.cm1", "w") as f:
    json.dump(mini_airways_map, f)
