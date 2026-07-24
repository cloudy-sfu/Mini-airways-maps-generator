import base64
import io

import numpy as np
from PIL import Image
from requests import Session

tile_px = 256
sess_map = Session()
sess_map.trust_env = False


def coord_to_web_mercator_tile(lon, lat, zoom):
    """
    Convert latitude and longitude to fractional Web-Mercator tile coords at specific
    zoom.
    :param lon:
    :param lat:
    :param zoom:
    :return:
    """
    assert -85.05112878 <= lat <= 85.05112878, \
        ("Cannot get the map near airport, because it's in polar regions (latitude > "
         "85.05).")
    x = (lon + 180) / 360 * (2 ** zoom)
    s = np.sin(np.deg2rad(lat))
    y = (0.5 - np.log((1 + s) / (1 - s)) / (4 * np.pi)) * (2 ** zoom)
    return x, y


def get_map(west_lon, east_lon, south_lat, north_lat, vertical_resolution):
    # Infer best zoom.
    _, y0 = coord_to_web_mercator_tile(0, north_lat, 0)
    _, y1 = coord_to_web_mercator_tile(0, south_lat, 0)
    z = int(np.clip(
        np.round(np.log2(vertical_resolution / ((y1 - y0) * tile_px)))
        , 0, 19
    ))
    x_w, y_n = coord_to_web_mercator_tile(west_lon, north_lat, z)
    x_e, y_s = coord_to_web_mercator_tile(east_lon, south_lat, z)
    tx0, tx1 = int(np.floor(x_w)), int(np.ceil(x_e))
    ty0, ty1 = int(np.floor(y_n)), int(np.ceil(y_s))

    # Stitch tiles into a canvas.
    canvas = Image.new("RGB", ((tx1 - tx0) * tile_px, (ty1 - ty0) * tile_px))
    for tx in range(tx0, tx1):
        for ty in range(ty0, ty1):
            background_map_response = sess_map.get(
                f"https://basemaps.cartocdn.com/dark_all/"
                f"{z}/{tx % (2 ** z)}/{ty % (2 ** z)}.png",
                headers={"User-Agent": "map-tool/1.0"}
            )
            canvas.paste(
                Image.open(io.BytesIO(background_map_response.content)).convert("RGB"),
                ((tx - tx0) * tile_px, (ty - ty0) * tile_px)
            )

    # Crop to exact bbox, then scale to fixed height.
    crop = canvas.crop((
        round((x_w - tx0) * tile_px), round((y_n - ty0) * tile_px),
        round((x_e - tx0) * tile_px), round((y_s - ty0) * tile_px)
    ))
    width = round(vertical_resolution * 16 / 9)
    background_map = crop.resize((width, vertical_resolution), Image.LANCZOS)

    # Base64 encode background map.
    background_map_stream = io.BytesIO()
    background_map.save(background_map_stream, format="PNG")
    background_map_bytes = background_map_stream.getvalue()
    background_map_bytes_encoded = base64.b64encode(background_map_bytes)
    background_map_str = background_map_bytes_encoded.decode("UTF-8")
    return background_map_str
