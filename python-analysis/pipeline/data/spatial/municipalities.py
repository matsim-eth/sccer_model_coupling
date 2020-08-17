import os

import geopandas as gpd

"""
This stage loads the Swiss municipality shapefiles.
"""


def configure(context):
    context.config("data_path")
    context.config("shp_path", "municipality_borders/ag-b-00.03-875-gg20/ggg_2020-LV95/shp/g1g20.shp")


def execute(context):

    # load municipality shapefile
    print("Loading municipality shapefile...")
    df_municipalities = gpd.read_file("%s/%s" % (context.config("data_path"), context.config("shp_path")),
                                      encoding="latin1").to_crs({'init': 'EPSG:2056'})
    df_municipalities = df_municipalities[["GMDNR", "geometry"]].rename({"GMDNR": "municipality_id"}, axis=1)

    return df_municipalities


def validate(context):
    if not os.path.exists("%s/%s" % (context.config("data_path"), context.config("shp_path"))):
        raise RuntimeError("Shapefile data is not available")

    return os.path.getsize("%s/%s" % (context.config("data_path"), context.config("shp_path")))
