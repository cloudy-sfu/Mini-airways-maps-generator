import os
import sqlite3
from argparse import ArgumentParser

import numpy as np
import pandas as pd

arg_parser = ArgumentParser()
arg_parser.add_argument("--db_path", required=True, type=str)
arg_parser.add_argument("--airport_id", required=True, type=int)
args, _ = arg_parser.parse_known_args()
db_path = os.path.join(args.db_path, "little_navmap_navigraph.sqlite")


def runway_angle(le_lon, le_lat, he_lon, he_lat):
    le_lat_rad = np.deg2rad(le_lat)
    he_lat_rad = np.deg2rad(he_lat)
    d_lon = np.deg2rad((he_lon - le_lon + 180) % 360 - 180)
    x = np.sin(d_lon) * np.cos(he_lat_rad)
    y = (np.cos(le_lat_rad) * np.sin(he_lat_rad) -
         np.sin(le_lat_rad) * np.cos(he_lat_rad) * np.cos(d_lon))
    return np.rad2deg(np.arctan2(x, y)) % 360


with open("tests/test_runway_heading.sql") as f:
    sql_runway_heading = f.read()
c = sqlite3.connect(db_path)
runways = pd.read_sql(sql_runway_heading, c,
                      params={"airport_id": args.airport_id})
c.close()

heading_calc = runway_angle(
    runways["primary_lonx"],
    runways["primary_laty"],
    runways["secondary_lonx"],
    runways["secondary_laty"],
)
print("Mean absolute error of angle (degree):",
      np.mean(np.abs(heading_calc - runways["heading"])))
