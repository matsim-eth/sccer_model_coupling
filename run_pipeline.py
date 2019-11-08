import os
import subprocess as sp
from optparse import OptionParser

# paths within repo
JAR_PATH = "./matsim-interface/target/sccer_model_coupling-0.0.1-SNAPSHOT.jar"
PYTHON_PATH = "./python-analysis/src/run"
DATA_PATH = "./data/00_raw"
TEMP_PATH = "./data/10_interim"
OUTPUT_PATH = "./data/20_final"

# external Euler paths
SCENARIOS_PATH = "/cluster/work/ivt_vpl/astra1802/output"
BEDDEM_PATH = "/cluster/work/ivt_vpl/tchervec/JA_Mobility_exchange/S000/BEDDEM-MATSIM"

# get command line options
option_parser = OptionParser()
option_parser.add_option("-y", "--year", dest="year", help="simulation year")
option_parser.add_option("-u", "--update", default=False, action="store_true", dest="update", help="flag to update outputs")
option_parser.add_option("-p", "--python", default="python", dest="python", help="python")
options, args = option_parser.parse_args()

year = options.year
update = options.update
python = options.python

# run features extraction
if update or not os.path.exists("{path}/{year}_plan_features.csv".format(path=TEMP_PATH, year=year)):
    print("feature extraction...")
    sp.check_call([
        "java", "-Xmx40g", "-cp", JAR_PATH, "ch.ethz.ivt.sccer.planfeatures.WriteSccerPlanFeatures",
        "{path}/bl_{year}_25pct/output_plans.xml.gz".format(path=SCENARIOS_PATH, year=year),
        "{path}/bl_{year}_25pct/output_network.xml.gz".format(path=SCENARIOS_PATH, year=year),
        "{path}/bl_{year}_25pct/output_events.xml.gz".format(path=SCENARIOS_PATH, year=year),
        "{path}/{year}_plan_features.csv".format(path=TEMP_PATH, year=year)
    ])

# run household extraction
if update or not os.path.exists("{path}/{year}_household_features.csv".format(path=TEMP_PATH, year=year)):
    print("household feature extraction...")
    sp.check_call([
        "java", "-Xmx40g", "-cp", JAR_PATH, "ch.ethz.ivt.sccer.planfeatures.WriteSccerHouseholdFeatures",
        "{path}/bl_{year}_25pct/output_plans.xml.gz".format(path=SCENARIOS_PATH, year=year),
        "{path}/bl_{year}_25pct/output_households.xml.gz".format(path=SCENARIOS_PATH, year=year),
        "{path}/{year}_household_features.csv".format(path=TEMP_PATH, year=year)
    ])

# run trips
if update or not os.path.exists("{path}/{year}_trips.csv".format(path=TEMP_PATH, year=year)):
    print("getting trips...")
    sp.check_call([
        "java", "-Xmx40g", "-cp", JAR_PATH, "ch.ethz.ivt.sccer.analysis.RunTripAnalysis",
        "--network-path", "{path}/bl_{year}_25pct/output_network.xml.gz".format(path=SCENARIOS_PATH, year=year),
        "--events-path", "{path}/bl_{year}_25pct/output_events.xml.gz".format(path=SCENARIOS_PATH, year=year),
        "--output-path", "{path}/{year}_trips.csv".format(path=TEMP_PATH, year=year)
    ])

# activity patterns with park time
if update or not os.path.exists("{path}/01_agent_clusters.{year}.csv".format(path=OUTPUT_PATH, year=year)):
    print("creating activity patterns with park time for STEM...")

    figure_dir = os.path.abspath("{path}/figures/{year}".format(path=OUTPUT_PATH, year=year))

    if not os.path.isdir(figure_dir):
        os.makedirs(figure_dir)

    sp.check_call([
        python, "{path}/01_activity_patterns_with_park_time.py".format(path=PYTHON_PATH),
        "--input", "{path}/{year}_plan_features.csv".format(path=TEMP_PATH, year=year),
        "--figure", "{path}/01_agent_clusters.{year}.png".format(path=figure_dir, year=year),
        "--output", "{path}/01_agent_clusters.{year}.csv".format(path=OUTPUT_PATH, year=year)
    ])

# travel distance with hh size
if update or not os.path.exists("{path}/02_agent_clusters.{year}.csv".format(path=OUTPUT_PATH, year=year)):
    print("creating travel distance with hh size for STEM...")

    figure_dir = os.path.abspath("{path}/figures/{year}".format(path=OUTPUT_PATH, year=year))

    if not os.path.isdir(figure_dir):
        os.makedirs(figure_dir)

    sp.check_call([
        python, "{path}/02_travel_distance_with_household_size.py".format(path=PYTHON_PATH),
        "--plans", "{path}/{year}_plan_features.csv".format(path=TEMP_PATH, year=year),
        "--households", "{path}/{year}_household_features.csv".format(path=TEMP_PATH, year=year),
        "--figure", "{path}/02_agent_clusters.{year}.png".format(path=figure_dir, year=year),
        "--output", "{path}/02_agent_clusters.{year}.csv".format(path=OUTPUT_PATH, year=year)
    ])

# trips for swissmod
if update or not os.path.exists("{path}/01-trips.{year}.csv".format(path=OUTPUT_PATH, year=year)):
    print("creating trips for Swissmod...")

    figure_dir = os.path.abspath("{path}/figures/{year}".format(path=OUTPUT_PATH, year=year))

    if not os.path.isdir(figure_dir):
        os.makedirs(figure_dir)

    sp.check_call([
        python, "{path}/03_merge_beddem_to_matsim_agents_for_swissmod.py".format(path=PYTHON_PATH),
        "--beddem-vehicles", "{path}/01-disaggregatedvehiclestock.{year}.csv".format(path=BEDDEM_PATH, year=year),
        "--beddem-trips", "{path}/03-trips.{year}.csv".format(path=BEDDEM_PATH, year=year),
        "--matsim-trips", "{path}/{year}_trips.csv".format(path=TEMP_PATH, year=year),
        "--municipality-shp", "{path}/shp/g1g18.shp".format(path=DATA_PATH),
        "--spatial-structure", "{path}/spatial_structure_2018.xlsx".format(path=DATA_PATH),
        "--fig-dir", figure_dir,
        "--fig-ext", "png",
        "--output", "{path}/01-trips.{year}.csv".format(path=OUTPUT_PATH, year=year)
    ])

