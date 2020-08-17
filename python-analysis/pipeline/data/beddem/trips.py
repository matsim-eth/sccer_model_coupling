import numpy as np
import pandas as pd


def configure(context):
    context.config("javs_path")
    context.config("scenario")
    context.config("year")


def execute(context):
    javs_path = context.config("javs_path")
    scenario = context.config("scenario")
    year = context.config("year")

    df_beddem = pd.read_csv("%s/%s/BEDDEM-MATSIM/03-trips.%s.csv" % (javs_path, scenario, year),
                            dtype={'AgentID': np.int64,
                                   'gemeindetype': np.int16,
                                   'Kanton': np.int16,
                                   'Day_Of_The_Week': np.int16,
                                   'Time_Start': np.float64,
                                   'Distance': np.float64,
                                   'Purpose': np.int16,
                                   'Mode': np.str,
                                   'Vehicle_Category': np.str,
                                   'Vehicle_Type': np.str,
                                   'Weather': np.str,
                                   'Weight_To_Universe': np.int16}
                            )

    df_beddem = df_beddem[df_beddem["Day_Of_The_Week"] == 2].copy()
    df_beddem = df_beddem.sort_values(["AgentID", "Time_Start"])

    return df_beddem
