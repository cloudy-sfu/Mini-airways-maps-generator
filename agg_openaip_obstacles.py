import json
import os
import sqlite3

import numpy as np
import pandas as pd

base_dir = "raw/openaip_obstacles"
obstacles = []
for fn in os.listdir(base_dir):
    fp = os.path.join(base_dir, fn)
    with open(fp) as f:
        obstacles_country = json.load(f)
    obstacles_country = pd.json_normalize(obstacles_country)
    obstacles.append(obstacles_country)
obstacles = pd.concat(obstacles, ignore_index=True)
obstacles["name"] = obstacles["name"].replace("Obstacle", pd.NA)
obstacles[["lon", "lat"]] = np.vstack(obstacles["geometry.coordinates"].values)
# https://en.wikipedia.org/wiki/Elevation#/media/File:Vertical_distances.svg
obstacles.rename(columns={
    # Always from mean sea level, in unit of meters.
    # Ref: https://docs.openaip.net/#/Obstacles/get_obstacles
    # -> Responses -> 200 -> Schema (above JSON code block)
    # -> items -> elevation -> unit & referenceDatum
    "elevation.value": "altitude",
    # Always from ground, in unit of meters.
    # Ref: (same root as above)
    # -> items -> height -> unit & referenceDatum
    "height.value": "height"
}, inplace=True)
# TODO: calc height from altitude & elevation, when height is not available.
obstacles = obstacles[[
    "country",
    "name",
    "altitude",
    "height",
    "lon",
    "lat",
]]

c = sqlite3.connect("raw/obstacles.sqlite")
# https://stackoverflow.com/questions/64419397/sqlite-max-variable-number-increase-or-break-sql-query-into-chunks
chunk_size = 32766 // obstacles.shape[1]  # "//": floor
obstacles.to_sql(
    "obstacles", c, if_exists="replace", method="multi", chunksize=chunk_size,
    index=False,
)
c.close()
