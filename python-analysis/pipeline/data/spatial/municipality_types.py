import os

import pandas as pd

"""
This stage loads the Swiss spatial structure data.
"""


def configure(context):
    context.config("data_path")
    context.config("structure_path", "spatial_structure_2018.xlsx")


def execute(context):

    # load spatial structure data
    print("Loading canton and municipality type data...")
    df_municipality_types = pd.read_excel("%s/%s" % (context.config("data_path"), context.config("structure_path")),
                                          names=["municipality_id", "canton_id", "municipality_type"],
                                          usecols=[0, 2, 21],
                                          skiprows=6,
                                          nrows=2229,
                                          )

    return df_municipality_types


def validate(context):
    if not os.path.exists("%s/%s" % (context.config("data_path"), context.config("structure_path"))):
        raise RuntimeError("Spatial structure data is not available")

    return os.path.getsize("%s/%s" % (context.config("data_path"), context.config("structure_path")))
