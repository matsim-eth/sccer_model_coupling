import os

import numpy as np
import pandas as pd

"""
This stage loads the raw trips from the microcensus.
"""


def configure(context):
    context.config("data_path")
    context.config("mz_path", "microcensus/wege.csv")


COLUMNS = ["HHNR", "f51100", "wzweck1", "wzweck2"]


def execute(context):
    data_path = context.config("data_path")
    mz_path = context.config("mz_path")

    df_mz_trips = pd.read_csv("%s/%s" % (data_path, mz_path), encoding="latin1")[COLUMNS]

    df_mz_trips = df_mz_trips.rename({"HHNR": "AgentID",
                                      "WEGNR": "trip_id",
                                      "f51100": "Time_Start",
                                      "wzweck1": "Purpose",
                                      "wzweck2": "returning"},
                                     axis=1)

    df_mz_trips.loc[:, "start_time"] = np.round(np.mod(np.floor(df_mz_trips.loc[:, "Time_Start"] / 60) + (
            df_mz_trips.loc[:, "Time_Start"] - np.floor(df_mz_trips.loc[:, "Time_Start"] / 60) * 60) / 100, 24), 1)

    df_mz_trips["returning"] = df_mz_trips["returning"] > 1
    df_mz_trips = df_mz_trips.drop("Time_Start", axis=1)
    df_mz_trips = df_mz_trips[["AgentID", "start_time", "Purpose", "returning"]]

    return df_mz_trips


def validate(context):
    if not os.path.exists("%s/%s" % (context.config("data_path"), context.config("mz_path"))):
        raise RuntimeError("MZ 2015 data is not available")

    return os.path.getsize("%s/%s" % (context.config("data_path"), context.config("mz_path")))
