import sqlite3

import numpy as np
import pandas as pd
from rasterio.features import shapes
from rasterio.io import MemoryFile
from rasterio.transform import rowcol
from requests import Session

with open("sql/open_topography_records.sql") as f:
    sql_open_topography_records = f.read()
with open("sql/insert_open_topography_records.sql") as f:
    insert_open_topography_records = f.read()
db_path = "raw/open_topography_records.sqlite"
session = Session()
session.trust_env = False


def check_rate_limit(dem_daily_limit):
    c = sqlite3.connect(db_path)
    try:
        open_topography_records = pd.read_sql(sql_open_topography_records, c)
    except pd.errors.DatabaseError:  # not exists | invalid table schema
        open_topography_records = pd.DataFrame(columns=["request_time"])  # text
        open_topography_records.to_sql("records", c, if_exists="replace", index=False)
    c.close()
    used = open_topography_records.shape[0]
    if used > dem_daily_limit - 1:  # This execution needs 1.
        now = pd.Timestamp('now', tz='UTC')
        first_valid = pd.to_datetime(open_topography_records.iloc[0, 0], utc=True)
        cd = pd.Timedelta(days=1)  # See also sql/open_topography_records.sql
        raise PermissionError(
            f"Requests to OpenTopography API exceed rate limit, which is "
            f"{dem_daily_limit} since {now - cd}). Please wait to {first_valid + cd}. "
            f"The program exits with error because cannot get digital elevation model."
        )


class DigitalElevationModel:
    def __init__(self, west_lon, east_lon, south_lat, north_lat, api_key):
        c = sqlite3.connect(db_path)
        if west_lon <= east_lon:
            response = session.get(
                "https://portal.opentopography.org/API/globaldem",
                params={
                    "demtype": "COP90",
                    "south": south_lat,
                    "north": north_lat,
                    "west": west_lon,
                    "east": east_lon,
                    "outputFormat": "AAIGrid",
                    "API_Key": api_key
                }
            )
            c.execute(insert_open_topography_records)
            # Open in memory, extract what we need, and close immediately
            with MemoryFile(response.content) as memfile:
                with memfile.open() as dataset:
                    self.dem_data = dataset.read(1)
                    self.transform = dataset.transform  # Map pixel -> (lon, lat)
        else:
            response_1 = session.get(
                "https://portal.opentopography.org/API/globaldem",
                params={
                    "demtype": "COP90",
                    "south": south_lat,
                    "north": north_lat,
                    "west": west_lon,
                    "east": 180,
                    "outputFormat": "AAIGrid",
                    "API_Key": api_key
                }
            )
            with MemoryFile(response_1.content) as memfile:
                with memfile.open() as dataset:
                    dem_data_1 = dataset.read(1)
                    self.transform = dataset.transform  # Map pixel -> (lon, lat)
            c.execute(insert_open_topography_records)
            response_2 = session.get(
                "https://portal.opentopography.org/API/globaldem",
                params={
                    "demtype": "COP90",
                    "south": south_lat,
                    "north": north_lat,
                    "west": -180,
                    "east": east_lon,
                    "outputFormat": "AAIGrid",
                    "API_Key": api_key
                }
            )
            with MemoryFile(response_2.content) as memfile:
                with memfile.open() as dataset:
                    dem_data_2 = dataset.read(1)
            c.execute(insert_open_topography_records)
            self.dem_data = np.hstack([dem_data_1, dem_data_2])
        c.commit()
        c.close()

    def check_point(self, lon, lat):
        i, j = rowcol(self.transform, lon, lat)
        if j < 0 or j >= self.dem_data.shape[1]:
            lon += 360
            i, j = rowcol(self.transform, lon, lat)
        return self.dem_data[i, j]

    def get_hills(self, elevation):
        if self.dem_data.max() < elevation:
            return []
        mask = (self.dem_data >= elevation).astype('uint8')  # format: image pixel
        shapes_ = shapes(mask, mask=mask, connectivity=8, transform=self.transform)
        # location_offset allow lon > 180 or lon < -180, no need to branch
        # cross_antimeridian.
        return [
            # Original coordinates is a closed shape, where the first point is the
            # same as last point, therefore we use [:-1].
            np.array(polygon["coordinates"][0][:-1])
            for polygon, _ in shapes_
            if polygon.get("type") == "Polygon"
        ]
