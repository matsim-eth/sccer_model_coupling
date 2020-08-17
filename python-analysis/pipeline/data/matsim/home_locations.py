import pandas as pd

import data.spatial.utils as spatial_utils

"""
This stage computes the home location for each MATSim agent.
"""


def configure(context):
    context.stage("data.matsim.trips")
    context.stage("data.spatial.municipalities")
    context.stage("data.spatial.municipality_types")


def execute(context):

    # load spatial structure data
    df_municipalities = context.stage("data.spatial.municipalities")
    df_municipality_types = context.stage("data.spatial.municipality_types")

    # load matsim trips
    df = context.stage("data.matsim.trips")[["person_id", "preceedingPurpose", "origin_x", "origin_y"]]

    # impute canton and municipality of agent's home location
    print("Selecting MATSim agent's home locations...")
    df = (df[df["preceedingPurpose"] == "home"]
        .drop_duplicates()
        .rename({"origin_x": "x", "origin_y": "y"}, axis=1)[["person_id", "x", "y"]])
    df = spatial_utils.to_gpd(context, df, "x", "y")
    df = df.drop(["x", "y"], axis=1)

    print("Imputing canton and municipality of home locations...")
    df = spatial_utils.impute(context, df, df_municipalities, "person_id", "municipality_id")
    df = pd.merge(df, df_municipality_types, on="municipality_id")
    df = df[["person_id", "canton_id", "municipality_id", "municipality_type"]]

    print(df.head(10))

    return df


# def validate(context):
#     return os.path.getsize("%s/%s" % (context.config("data_path"), context.config("structure_path")))
