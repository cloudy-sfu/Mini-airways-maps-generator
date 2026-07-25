from shapely.geometry import Polygon
from shapely import get_coordinates
import numpy as np


def make_ma_polygon(vertex_x, vertex_y, ext_dist=0.5):
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

    return {
        "x": center_x,
        "y": center_y,
        "innerPath": [
            {"x": vertex_x[i], "y": vertex_y[i]}
            for i in range(vertex_x.shape[0])
        ],
        "outerPath": [
            {"x": outer_path[i, 0], "y": outer_path[i, 1]}
            for i in outer_path.shape[0]
        ],
        "extDist": ext_dist,
    }


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
