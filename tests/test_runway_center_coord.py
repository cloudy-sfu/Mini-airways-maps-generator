import os
import sqlite3
from argparse import ArgumentParser

import numpy as np
import pandas as pd
from coord_to_dist import location_offset

arg_parser = ArgumentParser()
arg_parser.add_argument("--db_path", required=True, type=str)
arg_parser.add_argument("--airport_id", required=True, type=int)
args, _ = arg_parser.parse_known_args()
db_path = os.path.join(args.db_path, "little_navmap_navigraph.sqlite")

with open("tests/test_runway_center_coord.sql") as f:
    sql_runway_center_coord = f.read()


def middle_point(lat1, lon1, lat2, lon2, eps=1e-9):
    """Great-circle midpoint(s) of two sets of (lat, lon) in degrees.
    All inputs array-like (scalars OK) and broadcastable.
    Handles antimeridian and polar crossings element-wise.
    Antipodal pairs -> (nan, nan).
    Ref: http://www.movable-type.co.uk/scripts/latlong.html"""
    phi1, lambda1, phi2, lambda2 = map(
        np.radians, np.broadcast_arrays(lat1, lon1, lat2, lon2))

    # to Cartesian unit vectors
    x1, y1, z1 = np.cos(phi1)*np.cos(lambda1), np.cos(phi1)*np.sin(lambda1), np.sin(phi1)
    x2, y2, z2 = np.cos(phi2)*np.cos(lambda2), np.cos(phi2)*np.sin(lambda2), np.sin(phi2)

    # average
    xm, ym, zm = (x1+x2)/2, (y1+y2)/2, (z1+z2)/2

    mag = np.sqrt(xm*xm + ym*ym + zm*zm)   # antipodal detector
    hyp = np.sqrt(xm*xm + ym*ym)           # polar detector

    # base conversion (atan2 handles antimeridian wrap automatically)
    latm = np.degrees(np.arctan2(zm, hyp))
    lonm = np.degrees(np.arctan2(ym, xm))

    # edge case: midpoint on a pole -> lon arbitrary, set 0
    on_pole = hyp < eps
    lonm = np.where(on_pole, 0.0, lonm)

    # edge case: antipodal -> undefined
    antipodal = mag < eps
    latm = np.where(antipodal, np.nan, latm)
    lonm = np.where(antipodal, np.nan, lonm)

    return np.stack([latm, lonm], axis=-1)


c = sqlite3.connect(db_path)
runways = pd.read_sql(sql_runway_center_coord, c,
                      params={"airport_id": args.airport_id})
c.close()
middle_calc = middle_point(
    runways["primary_laty"],
    runways["primary_lonx"],
    runways["secondary_laty"],
    runways["secondary_lonx"],
)

dx, dy = location_offset(
    middle_calc[:, 1],
    middle_calc[:, 0],
    runways["lonx"],
    runways["laty"]
)

print("Mean X shift (m):", np.mean(dx) * 1000)
print("Mean Y shift (m):", np.mean(dy) * 1000)
