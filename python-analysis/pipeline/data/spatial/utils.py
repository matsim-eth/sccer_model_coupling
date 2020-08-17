import geopandas as gpd
import numpy as np
import pandas as pd
import shapely.geometry as geo
from sklearn.neighbors import KDTree


def to_gpd(context, df, x = "x", y = "y", crs = "epsg:2056", column = "geometry"):
    df[column] = [
        geo.Point(*coord) for coord in context.progress(
            zip(df[x], df[y]), total = len(df),
            label = "Converting coordinates"
        )]
    df = gpd.GeoDataFrame(df, crs = "epsg:2056", geometry = column)

    if not crs == "epsg:2056":
        df = df.to_crs("epsg:2056")

    return df


def impute(context, df_points, df_zones, point_id_field, zone_id_field, fix_by_distance=True, chunk_size=10000):
    assert(type(df_points) == gpd.GeoDataFrame)
    assert(type(df_zones) == gpd.GeoDataFrame)

    assert(point_id_field in df_points.columns)
    assert(zone_id_field in df_zones.columns)
    assert(not zone_id_field in df_points.columns)

    df_original = df_points
    df_points = df_points[[point_id_field, "geometry"]]
    df_zones = df_zones[[zone_id_field, "geometry"]]

    print("Imputing %d zones into %d points by spatial join..." % (len(df_zones), len(df_points)))

    result = []
    chunk_count = max(1, int(len(df_points) / chunk_size))
    for chunk in context.progress(np.array_split(df_points, chunk_count), total=chunk_count):
        result.append(gpd.sjoin(df_zones, chunk, op="contains", how="right"))
    df_points = pd.concat(result).reset_index()

    if "left_index" in df_points: del df_points["left_index"]
    if "right_index" in df_points: del df_points["right_index"]

    invalid_mask = pd.isnull(df_points[zone_id_field])

    if fix_by_distance and np.any(invalid_mask):
        print("  Fixing %d points by centroid distance join..." % np.count_nonzero(invalid_mask))
        coordinates = np.vstack([df_zones["geometry"].centroid.x, df_zones["geometry"].centroid.y]).T
        kd_tree = KDTree(coordinates)

        df_missing = df_points[invalid_mask]
        coordinates = np.vstack([df_missing["geometry"].centroid.x, df_missing["geometry"].centroid.y]).T
        indices = kd_tree.query(coordinates, return_distance=False).flatten()

        df_points.loc[invalid_mask, zone_id_field] = df_zones.iloc[indices][zone_id_field].values

    return pd.merge(df_original, df_points[[point_id_field, zone_id_field]], on=point_id_field, how="left")