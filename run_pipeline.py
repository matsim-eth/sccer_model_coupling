import os
import subprocess as sp
from optparse import OptionParser

# # external Euler paths
# SCENARIOS_PATH = "/cluster/work/ivt_vpl/astra1802/output/bl_{year}_25pct"
# BEDDEM_PATH = "/cluster/work/ivt_vpl/tchervec/JA_Mobility_exchange/S000/BEDDEM-MATSIM"

# get script directory
script_dir = os.path.dirname(os.path.realpath(__file__))

# get command line options
option_parser = OptionParser()

# internal paths
option_parser.add_option("-j", "--jar-path", default="{path}/matsim-interface/target/sccer_model_coupling-0.0.1-SNAPSHOT.jar".format(path=script_dir), dest="jar_path", help="jar path")
option_parser.add_option("-p", "--python-path", default="{path}/python-analysis/src/run".format(path=script_dir), dest="python_path", help="python analysis path")
option_parser.add_option("-d", "--raw-data-path", default="{path}/data/00_raw".format(path=script_dir), dest="raw_data_path", help="raw data path")
option_parser.add_option("-t", "--temp-data-path", default="{path}/data/10_interim".format(path=script_dir), dest="temp_data_path", help="temp data path")
option_parser.add_option("-o", "--output-data-path", default="{path}/data/20_final".format(path=script_dir), dest="output_data_path", help="final output path")

# external paths
option_parser.add_option("-s", "--scenario-path", dest="scenario_path", help="scenario path")
option_parser.add_option("-b", "--beddem-path", dest="beddem_path", help="beddem data path")

# other
option_parser.add_option("-y", "--year", dest="year", help="simulation year")
option_parser.add_option("-u", "--update", default=False, action="store_true", dest="update", help="flag to update outputs")
option_parser.add_option("-m", "--memory", default='12g', dest="mem", help="java memory (ex. 40g), default = 12g")

# parse options
(options, args) = option_parser.parse_args()

# print entered options
for option, value in options.__dict__.items():
    print(option,":", value)

# paths within repo
jar_path = options.jar_path
python_path = options.python_path
data_path = options.raw_data_path
temp_path = options.temp_data_path
output_path = options.output_data_path

# external Euler paths
scenario_path = options.scenario_path
beddem_path = options.beddem_path

year = options.year
update = options.update


# run features extraction
if update or not os.path.exists("{path}/{year}/plan_features.csv".format(path=temp_path, year=year)):
    print("\nfeature extraction...")

    temp_year_dir = os.path.abspath("{path}/{year}".format(path=temp_path, year=year))

    if not os.path.isdir(temp_year_dir):
        os.makedirs(temp_year_dir)

    sp.check_call([
        "java", "-Xmx40g", "-cp", jar_path, "ch.ethz.ivt.sccer.planfeatures.WriteSccerPlanFeatures",
        "{path}/output_plans.xml.gz".format(path=scenario_path),
        "{path}/output_network.xml.gz".format(path=scenario_path),
        "{path}/output_events.xml.gz".format(path=scenario_path),
        "{path}/plan_features.csv".format(path=temp_year_dir)
    ])

# run household extraction
if update or not os.path.exists("{path}/{year}/household_features.csv".format(path=temp_path, year=year)):
    print("\nhousehold feature extraction...")

    temp_year_dir = os.path.abspath("{path}/{year}".format(path=temp_path, year=year))

    if not os.path.isdir(temp_year_dir):
        os.makedirs(temp_year_dir)

    sp.check_call([
        "java", "-Xmx40g", "-cp", jar_path, "ch.ethz.ivt.sccer.planfeatures.WriteSccerHouseholdFeatures",
        "{path}/output_plans.xml.gz".format(path=scenario_path),
        "{path}/output_households.xml.gz".format(path=scenario_path),
        "{path}/household_features.csv".format(path=temp_year_dir)
    ])

# run trips
if update or not os.path.exists("{path}/{year}/trips.csv".format(path=temp_path, year=year)):
    print("\ngetting trips...")

    temp_year_dir = os.path.abspath("{path}/{year}".format(path=temp_path, year=year))

    if not os.path.isdir(temp_year_dir):
        os.makedirs(temp_year_dir)

    sp.check_call([
        "java", "-Xmx40g", "-cp", jar_path, "ch.ethz.ivt.sccer.analysis.RunTripAnalysis",
        "--network-path", "{path}/output_network.xml.gz".format(path=scenario_path),
        "--events-path", "{path}/output_events.xml.gz".format(path=scenario_path),
        "--output-path", "{path}/trips.csv".format(path=temp_year_dir)
    ])

# activity patterns with park time
if update or not os.path.exists("{path}/{year}/01_agent_clusters.{year}.csv".format(path=output_path, year=year)):
    print("\ncreating activity patterns with park time for STEM...")

    output_year_dir = os.path.abspath("{path}/{year}".format(path=output_path, year=year))
    if not os.path.isdir(output_year_dir):
        os.makedirs(output_year_dir)

    output_figure_dir = os.path.abspath("{path}/figures".format(path=output_year_dir))
    if not os.path.isdir(output_figure_dir):
        os.makedirs(output_figure_dir)

    sp.check_call([
        "python", "{path}/01_activity_patterns_with_park_time.py".format(path=python_path),
        "--input", "{path}/{year}/plan_features.csv".format(path=temp_path, year=year),
        "--figure", "{path}/01_agent_clusters.{year}.png".format(path=output_figure_dir, year=year),
        "--output", "{path}/01_agent_clusters.{year}.csv".format(path=output_year_dir, year=year)
    ])

# travel distance with hh size
if update or not os.path.exists("{path}/{year}/02_agent_clusters.{year}.csv".format(path=output_path, year=year)):
    print("\ncreating travel distance with hh size for STEM...")

    output_year_dir = os.path.abspath("{path}/{year}".format(path=output_path, year=year))
    if not os.path.isdir(output_year_dir):
        os.makedirs(output_year_dir)

    output_figure_dir = os.path.abspath("{path}/figures".format(path=output_year_dir))
    if not os.path.isdir(output_figure_dir):
        os.makedirs(output_figure_dir)

    sp.check_call([
        "python", "{path}/02_travel_distance_with_household_size.py".format(path=python_path),
        "--plans", "{path}/{year}/plan_features.csv".format(path=temp_path, year=year),
        "--households", "{path}/{year}/household_features.csv".format(path=temp_path, year=year),
        "--figure", "{path}/02_agent_clusters.{year}.png".format(path=output_figure_dir, year=year),
        "--output", "{path}/02_agent_clusters.{year}.csv".format(path=output_year_dir, year=year)
    ])

# trips for swissmod
if update or not os.path.exists("{path}/{year}/01-trips.{year}.csv".format(path=output_path, year=year)):
    print("\ncreating trips for Swissmod...")

    output_year_dir = os.path.abspath("{path}/{year}".format(path=output_path, year=year))
    if not os.path.isdir(output_year_dir):
        os.makedirs(output_year_dir)

    output_figure_dir = os.path.abspath("{path}/figures".format(path=output_year_dir))
    if not os.path.isdir(output_figure_dir):
        os.makedirs(output_figure_dir)

    sp.check_call([
        "python", "{path}/03_merge_beddem_to_matsim_agents_for_swissmod.py".format(path=python_path),
        "--beddem-vehicles", "{path}/01-disaggregatedvehiclestock.{year}.csv".format(path=beddem_path, year=year),
        "--beddem-trips", "{path}/03-trips.{year}.csv".format(path=beddem_path, year=year),
        "--matsim-trips", "{path}/{year}/trips.csv".format(path=temp_path, year=year),
        "--municipality-shp", "{path}/shp/g1g18.shp".format(path=data_path),
        "--spatial-structure", "{path}/spatial_structure_2018.xlsx".format(path=data_path),
        "--fig-dir", output_figure_dir,
        "--fig-ext", "png",
        "--output", "{path}/01-trips.{year}.csv".format(path=output_year_dir, year=year)
    ])

