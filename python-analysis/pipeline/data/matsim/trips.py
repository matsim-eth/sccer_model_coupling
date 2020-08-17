import os.path

import numpy as np
import pandas as pd

import matsim.runtime.eqasim as eqasim


def configure(context):
    context.stage("matsim.runtime.java")
    context.stage("matsim.runtime.eqasim")
    context.config("scenario_path")
    context.config("year")


def execute(context):
    scenario_path = "%s%s" % ( context.config("scenario_path"), context.config("year"))
    output_path = "%s/simulation_output/trips.csv" % (scenario_path)

    # Run routing
    eqasim.run(context, "org.eqasim.core.analysis.RunTripAnalysis", [
        "--network-path", "%s/simulation_output/output_network.xml.gz" % (scenario_path),
        "--output-path", output_path,
        "--population-path", "%s/simulation_output/output_plans.xml.gz" % (scenario_path),
        "--stage-activity-types", '''"bike interaction, pt interaction, car interaction, car_passenger interaction"''',
        "--network-modes", "car",
        "--input-distance-units", "meter",
        "--output-distance-units", "meter"
    ])

    assert os.path.exists(output_path)

    df_trips = pd.read_csv(filepath_or_buffer=output_path, sep=";",
                           dtype={'person_id': np.str,
                                  'person_trip_id': np.int16,
                                  'origin_x': np.float64,
                                  'origin_y': np.float64,
                                  'destination_x': np.float64,
                                  'destination_y': np.float64,
                                  'start_time': np.float32,
                                  'travel_time': np.float32,
                                  'network_distance': np.float64,
                                  'mode': np.str,
                                  'preceedingPurpose': np.str,
                                  'followingPurpose': np.str,
                                  'returning': np.bool,
                                  'crowfly_distance': np.float64})

    # dropping trips with freight agents
    df_trips = df_trips[~df_trips["person_id"].str.contains("freight")]

    # convert ids to int
    df_trips["person_id"] = df_trips["person_id"].astype(np.int64)

    # convert distances to km
    df_trips['network_distance'] = df_trips['network_distance'] / 1000
    df_trips['crowfly_distance'] = df_trips['crowfly_distance'] / 1000

    return df_trips


