import os.path

import pandas as pd

import numpy as np

import matsim.runtime.matsim_interface as matsim_interface

"""
This stage extracts the MZ ids for the MATSim agents.
"""


def configure(context):
    context.stage("matsim.runtime.java")
    context.stage("matsim.runtime.matsim_interface")
    context.config("year")
    context.config("scenario_path")


def execute(context):
    year = context.config("year")
    scenario_path = context.config("scenario_path")
    output_path = "%s%s/mz_person_id.csv" % (scenario_path, year)

    matsim_interface.run(context, "ch.ethz.ivt.sccer.analysis.ExtractMicrocensusID", [
        "--population-path", "%s%s/switzerland_population.xml.gz" % (scenario_path, year),
        "--output-path", output_path
    ])

    assert os.path.exists(output_path)

    df = pd.read_csv(filepath_or_buffer=output_path, sep=";")

    df = df[df["mz_person_id"] != -1]

    print(df)

    return df


def validate(context):
    return
