import numpy as np

# https://en.wikipedia.org/wiki/Earth
r = 6378.137


def location_offset(base_lon, base_lat, lon, lat):
    # https://en.wikipedia.org/wiki/Equirectangular_projection
    base_lon = np.deg2rad(base_lon)
    base_lat = np.deg2rad(base_lat)
    lon = np.deg2rad(lon)
    lat = np.deg2rad(lat)
    dx = r * np.cos(base_lat) * (lon - base_lon)
    dy = r * (lat - base_lat)
    # Unit: km
    return dx, dy


def location_offset_inverse(base_lon, base_lat, dx, dy):
    # Exact inverse of location_offset (equirectangular projection)
    # https://en.wikipedia.org/wiki/Equirectangular_projection
    base_lon = np.deg2rad(base_lon)
    base_lat = np.deg2rad(base_lat)
    lon = base_lon + dx / (r * np.cos(base_lat))
    lat = base_lat + dy / r
    lon = np.rad2deg(lon)
    lat = np.rad2deg(lat)
    return lon, lat
