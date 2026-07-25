import numpy as np

# https://en.wikipedia.org/wiki/Earth Unit: km.
r = 6378.137
# Equirectangular projection boundary. Unit: radian.
min_lat = np.deg2rad(-85)
max_lat = np.deg2rad(85)


def location_offset(base_lon, base_lat, lon, lat):
    # https://en.wikipedia.org/wiki/Equirectangular_projection
    base_lon = np.deg2rad(base_lon)
    base_lat = np.deg2rad(base_lat)
    lon = np.deg2rad(lon)
    lat = np.deg2rad(lat)
    d_lon = (lon - base_lon + np.pi) % (2 * np.pi) - np.pi  # antimeridian safe
    dx = r * np.cos(base_lat) * d_lon
    dy = r * (lat - base_lat)
    # Unit: km
    return dx, dy


def location_offset_inverse(base_lon, base_lat, dx, dy):
    # Exact inverse of location_offset (equirectangular projection)
    # https://en.wikipedia.org/wiki/Equirectangular_projection
    base_lon = np.deg2rad(base_lon)
    base_lat = np.deg2rad(base_lat)
    lon = base_lon + dx / (r * np.cos(base_lat))
    lon = (lon + np.pi) % (2 * np.pi) - np.pi  # antimeridian safe
    lat = base_lat + dy / r
    lat_valid = (base_lat > min_lat) & (base_lat < max_lat) & \
                (lat > min_lat) & (lat < max_lat)
    lon = np.where(lat_valid, lon, np.nan)
    lat = np.where(lat_valid, lat, np.nan)
    lon = np.rad2deg(lon)
    lat = np.rad2deg(lat)
    return lon, lat
