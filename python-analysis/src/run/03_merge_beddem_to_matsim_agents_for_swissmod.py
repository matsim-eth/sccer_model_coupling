from optparse import OptionParser

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import shapely.geometry as geo
from sklearn.neighbors import KDTree
from tqdm import tqdm

option_parser = OptionParser()
option_parser.add_option("--beddem-vehicles", dest="beddem_vehicles", help="BEDDEM disaggregated vehicle stock")
option_parser.add_option("--beddem-trips", dest="beddem_trips", help="BEDDEM trips")
option_parser.add_option("--matsim-trips", dest="matsim_trips", help="MATSim trips")
option_parser.add_option("--municipality-shp", dest="mun_shp", help="Shapefile of Swiss municipalities")
option_parser.add_option("--spatial-structure", dest="spatial_structure", help="Swiss spatial structure data")
option_parser.add_option("--consider-cantons", default=False, action="store_true", dest="consider_cantons", help="flag whether to consider cantons when matching")
option_parser.add_option("--fig-dir", dest="fig_dir", help="output directory for figures")
option_parser.add_option("--fig-ext", dest="fig_ext", help="figure file extension")
option_parser.add_option("--output", dest="output", help="output path for output csv")
options, args = option_parser.parse_args()


# # BEDDEM filtering
print("--- BEDDEM ---")

# load in vehicle stock
print("Loading disaggregated vehicle stock...")
print(options.beddem_vehicles)
df_vehicles = pd.read_csv(filepath_or_buffer=options.beddem_vehicles)
df_vehicles = df_vehicles.rename({"ID": "agent_id",
                                  "Type_Of_Vehicle": "vehicle_type",
                                  "Powertrain": "powertrain",
                                  "Cons": "consumption"}, axis=1)
df_vehicles = df_vehicles[["vehicle_type", "powertrain", "consumption", "CO2"]]
df_vehicles = df_vehicles.groupby(["vehicle_type", "powertrain"]).mean().reset_index()
print(df_vehicles.head(3))

# load in trips
print("Loading trips...")
print(options.beddem_trips)
df_trips = pd.read_csv(filepath_or_buffer=options.beddem_trips)
print("number of unique agents:", len(df_trips["AgentID"].unique()))
print("vehicle categories:", df_trips["Vehicle_Category"].unique())
print(df_trips.sort_values("AgentID").head(3))

# select only car trips
print("Filtering car trips...")
df_trips = df_trips[df_trips["Mode"] == "Car"].reset_index(drop=True)
df_trips = df_trips.rename({"AgentID": "agent_id",
                            "gemeindetype": "municipality_type",
                            "Kanton": "canton",
                            "Vehicle_Category": "vehicle_type",
                            "Vehicle_Type": "powertrain",
                            "Day_Of_The_Week": "day_of_week",
                            "Time_Start": "time_start",
                            "Weather": "weather",
                            "Mode": "mode",
                            "Distance": "distance",
                            "Purpose": "purpose",
                            "Weight_To_Universe": "weight"}, axis=1)
print("number of unique car-driving agents:", len(df_trips["agent_id"].unique()))
print("vehicle categories:", df_trips["vehicle_type"].unique())
print(df_trips.sort_values("agent_id").head())

# merge vehicle info
print("Merging vehicle info onto trips...")
df_trips_beddem = pd.merge(df_trips,
                           df_vehicles,
                           on=["vehicle_type", "powertrain"])
df_trips_beddem = df_trips_beddem[["agent_id",
                                   "municipality_type",
                                   "canton",
                                   "day_of_week",
                                   "mode",
                                   "distance",
                                   "vehicle_type",
                                   "powertrain",
                                   "consumption",
                                   "weight"]]
df_trips_beddem = df_trips_beddem.sort_values(["agent_id", "day_of_week"])
print("number of unique agents:", len(df_trips_beddem["agent_id"].unique()))
print(df_trips_beddem.head(3))

# aggregate distance travelled by car
print("Aggregating distance travelled by car...")
df_trips_beddem = df_trips_beddem[df_trips_beddem["day_of_week"] < 5]
df_agents_beddem = (df_trips_beddem
                    .groupby(["agent_id", "municipality_type",
                              "canton", "day_of_week",
                              "vehicle_type", "powertrain",
                              "consumption", "weight"])["distance"]
                    .agg(["sum", "count"])
                    .rename(columns={"sum": "distance", "count": "number_trips"})
                    .reset_index()
                    .groupby(["agent_id", "municipality_type",
                              "canton", "vehicle_type",
                              "powertrain", "consumption"])
                    .mean()
                    .reset_index()
                    )
print("number of unique agents:", len(df_agents_beddem["agent_id"].unique()))
print(df_agents_beddem.head(3))


# # MATSim filtering
print("--- MATSim ---")

# load in trips (MATSim)
print("Loading trips...")
df_trips_matsim = pd.read_csv(filepath_or_buffer=options.matsim_trips, sep=";")

# dropping trips with freight agents
df_trips_matsim = df_trips_matsim[~df_trips_matsim["person_id"].str.contains("freight")]

# convert ids to int
df_trips_matsim["person_id"] = df_trips_matsim["person_id"].astype(np.int64)

# convert distances to km
df_trips_matsim['network_distance'] = df_trips_matsim['network_distance'] / 1000
df_trips_matsim['crowfly_distance'] = df_trips_matsim['crowfly_distance'] / 1000
print(df_trips_matsim.head(10))

# filter only car trips
print("Filtering car trips...")
df_trips_car = df_trips_matsim[df_trips_matsim["mode"] == "car"]

# remove trips under 1 m
print("Removing trips under 1 m...")
df_trips_car = df_trips_car[df_trips_car["network_distance"] > 0.001]
print(df_trips_car.head(3))

# aggregate distance travelled by car
print("Aggregating distance travelled by car...")
df_trips_matsim_agg = (df_trips_car[["person_id","network_distance"]]
                       .sort_values("person_id")
                       .groupby("person_id")["network_distance"]
                       .agg(["sum", "count"])
                       .rename(columns={"sum": "network_distance", "count": "number_trips"})
                       .reset_index()
                       )
print(df_trips_matsim_agg.head(3))


## Spatial data
print("--- SPATIAL DATA ---")

# load municipality shapefile
print("Loading municipality shapefile...")
print(options.mun_shp)
df_municipalities = gpd.read_file(options.mun_shp, encoding = "latin1").to_crs({'init': 'EPSG:2056'})
df_municipalities = df_municipalities[["GMDNR", "geometry"]].rename({"GMDNR":"municipality_id"}, axis=1)
print(df_municipalities.head(3))

# load spatial structure data
print("Loading canton and municipality type data...")
print(options.spatial_structure)
df_municipality_types = pd.read_excel(options.spatial_structure,
                                      names=["municipality_id", "canton_id", "municipality_type"],
                                      usecols=[0, 2, 21],
                                      skiprows=6,
                                      nrows=2229,
                                      )
print(df_municipality_types.head(3))


def to_gpd(df, x="x", y="y", crs={"init": "epsg:2056"}):
    df["geometry"] = [
        geo.Point(*coord) for coord in tqdm(
            zip(df[x], df[y]), total=len(df),
            desc="Converting coordinates"
        )]
    df = gpd.GeoDataFrame(df)
    df.crs = crs

    if not crs == {"init": "epsg:2056"}:
        df = df.to_crs({"init": "epsg:2056"})

    return df


def impute(df_points, df_zones, point_id_field, zone_id_field, fix_by_distance=True, chunk_size=10000):
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
    for chunk in tqdm(np.array_split(df_points, chunk_count), total=chunk_count):
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


# impute canton and municipality of agent's home location
print("Selecting MATSim agent's home locations...")
df_home_matsim = df_trips_matsim[["person_id", "preceedingPurpose", "origin_x", "origin_y"]]
df_home_matsim = df_home_matsim[df_home_matsim["preceedingPurpose"] == "home"]
df_home_matsim = (df_home_matsim.drop_duplicates()
    .rename({"origin_x": "x", "origin_y": "y"}, axis=1)[["person_id", "x", "y"]])
df_home_matsim = to_gpd(df_home_matsim, "x", "y")
df_home_matsim = df_home_matsim.drop(["x", "y"], axis=1)
print(df_home_matsim.head(3))

print("Imputing canton and municipality of home locations...")
df_home = impute(df_home_matsim, df_municipalities, "person_id", "municipality_id")
df_home = pd.merge(df_home, df_municipality_types, on="municipality_id")
df_home = df_home[["person_id", "canton_id", "municipality_type"]]
print(df_home.head(3))

# merge spatial info
print("Merging home location info onto MATSim trips...")
df_trips_matsim_agg = pd.merge(df_trips_matsim_agg, df_home, on="person_id")
df_trips_matsim_agg = df_trips_matsim_agg.sort_values(["canton_id", "municipality_type"])
print(df_trips_matsim_agg.head())


# # Matching
print("--- MATCHING ---")

print(df_trips_matsim_agg.head(3))
print(df_agents_beddem.head(3))

# set some default values
df_trips_matsim_agg["agent_id"] = 0
df_trips_matsim_agg["canton_id_beddem"] = 0
df_trips_matsim_agg["municipality_type_beddem"] = 0
df_trips_matsim_agg["vehicle_type"] = ''
df_trips_matsim_agg["powertrain"] = ''
df_trips_matsim_agg["consumption"] = 0
df_trips_matsim_agg["distance_beddem"] = 0
df_trips_matsim_agg["number_trips_beddem"] = 0

# match MATSim agents to BedDem agents
municipality_types = df_trips_matsim_agg["municipality_type"].unique()

with tqdm(desc="Matching MATSim agents to BedDem agents", total=len(municipality_types)) as municipality_progress:
    for municipality_type in municipality_types:

        # create MATSim municipality filter
        f_matsim_municipality = (df_trips_matsim_agg["municipality_type"] == municipality_type)

        # create BEDDEM filters
        f_beddem_m_c = np.ones(len(df_agents_beddem), dtype=np.bool)
        f_beddem_municipality = (df_agents_beddem["municipality_type"] == municipality_type)

        # create KDtree from BEDDEM agents using municipalities only
        coordinates_municipality = np.vstack([df_agents_beddem.loc[f_beddem_municipality, "distance"].values]).T
        kd_tree_municipality = KDTree(coordinates_municipality)

        canton_ids = df_trips_matsim_agg.loc[f_matsim_municipality, "canton_id"].unique()
        for canton_id in canton_ids:

            # get relevant MATSim agents
            f_matsim_canton = (df_trips_matsim_agg["canton_id"] == canton_id)
            f_matsim_m_c = (f_matsim_canton & f_matsim_municipality)

            # get relevant BEDDEM agents
            f_beddem_canton = (df_agents_beddem["canton"] == canton_id)
            f_beddem_m_c = (f_beddem_canton & f_beddem_municipality)

            # if no match, only consider municipality type
            if (np.sum(f_beddem_m_c) == 0):
                f_beddem_m_c = f_beddem_municipality

            # create KDtree from BEDDEM agents using both municipalities and cantons
            coordinates_municipality_canton = np.vstack([df_agents_beddem.loc[f_beddem_m_c, "distance"].values]).T
            kd_tree_municipality_canton = KDTree(coordinates_municipality_canton)

            # try to match MATSim agents using both municipalities and cantons
            matsim_pts = np.vstack([df_trips_matsim_agg.loc[f_matsim_m_c, "network_distance"].values]).T
            (distances, indices) = kd_tree_municipality_canton.query(matsim_pts, return_distance=True)
            indices = indices.flatten()
            distances = distances.flatten()

            # get matches within 1 km
            f_direct = distances <= 5
            f_matsim_m_c_direct = np.zeros(np.shape(f_matsim_m_c), dtype=bool)
            f_matsim_m_c_direct[f_matsim_m_c] = f_direct
            df_matches_direct = df_agents_beddem.loc[f_beddem_m_c, :].iloc[list(indices[f_direct])]

            # get matched data
            df_trips_matsim_agg.loc[f_matsim_m_c_direct, "agent_id"] = df_matches_direct.loc[:, "agent_id"].values
            df_trips_matsim_agg.loc[f_matsim_m_c_direct, "canton_id_beddem"] = df_matches_direct.loc[:, "canton"].values
            df_trips_matsim_agg.loc[f_matsim_m_c_direct, "municipality_type_beddem"] = df_matches_direct.loc[:, "municipality_type"].values
            df_trips_matsim_agg.loc[f_matsim_m_c_direct, "vehicle_type"] = df_matches_direct.loc[:, "vehicle_type"].values
            df_trips_matsim_agg.loc[f_matsim_m_c_direct, "powertrain"] = df_matches_direct.loc[:, "powertrain"].values
            df_trips_matsim_agg.loc[f_matsim_m_c_direct, "consumption"] = df_matches_direct.loc[:, "consumption"].values
            df_trips_matsim_agg.loc[f_matsim_m_c_direct, "distance_beddem"] = df_matches_direct.loc[:, "distance"].values
            df_trips_matsim_agg.loc[f_matsim_m_c_direct, "number_trips_beddem"] = df_matches_direct.loc[:, "number_trips"].values

            # try to match only with municipalities otherwise, if there is anything left to match
            if np.sum(~f_direct) > 0:
                matsim_pts_indirect = matsim_pts[~f_direct]
                (distances_indirect, indices_indirect) = kd_tree_municipality.query(matsim_pts_indirect, return_distance=True)
                distances_indirect = distances_indirect.flatten()
                indices_indirect = indices_indirect.flatten()

                f_matsim_m_c_indirect = np.zeros(np.shape(f_matsim_m_c), dtype=bool)
                f_matsim_m_c_indirect[f_matsim_m_c] = ~f_direct

                df_matches_indirect = df_agents_beddem.loc[f_beddem_municipality, :].iloc[list(indices_indirect)]
                df_trips_matsim_agg.loc[f_matsim_m_c_indirect, "agent_id"] = df_matches_indirect.loc[:, "agent_id"].values
                df_trips_matsim_agg.loc[f_matsim_m_c_indirect, "canton_id_beddem"] = df_matches_indirect.loc[:, "canton"].values
                df_trips_matsim_agg.loc[f_matsim_m_c_indirect, "municipality_type_beddem"] = df_matches_indirect.loc[:, "municipality_type"].values
                df_trips_matsim_agg.loc[f_matsim_m_c_indirect, "vehicle_type"] = df_matches_indirect.loc[:, "vehicle_type"].values
                df_trips_matsim_agg.loc[f_matsim_m_c_indirect, "powertrain"] = df_matches_indirect.loc[:, "powertrain"].values
                df_trips_matsim_agg.loc[f_matsim_m_c_indirect, "consumption"] = df_matches_indirect.loc[:, "consumption"].values
                df_trips_matsim_agg.loc[f_matsim_m_c_indirect, "distance_beddem"] = df_matches_indirect.loc[:, "distance"].values
                df_trips_matsim_agg.loc[f_matsim_m_c_indirect, "number_trips_beddem"] = df_matches_indirect.loc[:, "number_trips"].values

        municipality_progress.update()

print(df_trips_matsim_agg.head(3))


# # Comparing results
print("--- MATCHING RESULTS ---")
# distance matching -- scatter plot
print("distance matching: scatter plot")
plt.figure(dpi=120)
plt.plot(df_trips_matsim_agg["network_distance"].values, df_trips_matsim_agg["distance_beddem"].values, ".")
plt.xlabel("MATSim daily distance by car (km)")
plt.ylabel("BEDDEM daily distance by car (km)")
print("Plotting results...")
plt.savefig('{dir}/distance_scatter.{ext}'.format(dir=options.fig_dir, ext=options.fig_ext))

# distance matching -- relative error
print("distance matching: relative error")
plt.figure(dpi=120)
dist_rel_err = np.abs(df_trips_matsim_agg["network_distance"].values - df_trips_matsim_agg["distance_beddem"].values) / df_trips_matsim_agg["network_distance"].values
dist_rel_err = dist_rel_err[dist_rel_err < 1 ]
plt.hist(dist_rel_err, 100)
plt.xlim((0,1))
plt.xlabel("Relative error on daily distance by car")
print("Plotting results...")
plt.savefig('{dir}/distance_comparison.{ext}'.format(dir=options.fig_dir, ext=options.fig_ext))
print("Error <= 25%:", np.sum(dist_rel_err <= 0.25) / len(df_trips_matsim_agg))
print("Error > 25%:", np.sum(dist_rel_err > 0.25) / len(df_trips_matsim_agg))

# number of trips matching -- absolute error
print("number of trips matching: absolute error")
plt.figure(dpi=120)
trips_abs_err = np.abs(df_trips_matsim_agg["number_trips"].values - df_trips_matsim_agg["number_trips_beddem"].values)
plt.hist(trips_abs_err, 100)
plt.xlim((0,10))
plt.xlabel("Absolute error on number of car trips")
print("Plotting results...")
plt.savefig('{dir}/number_trips_comparison.{ext}'.format(dir=options.fig_dir, ext=options.fig_ext))
print("Absolute error <= 2 trips:", np.sum(trips_abs_err <= 2) / len(df_trips_matsim_agg))
print("Absolute error > 2 trips:", np.sum(trips_abs_err > 2) / len(df_trips_matsim_agg))

# compare canton matching
print("Comparing canton matching...")
print("Correctly matched cantons:",np.sum(df_trips_matsim_agg["canton_id"].values == df_trips_matsim_agg["canton_id_beddem"].values) / len(df_trips_matsim_agg))
print("Incorrectly matched cantons:",np.sum(df_trips_matsim_agg["canton_id"].values != df_trips_matsim_agg["canton_id_beddem"].values) / len(df_trips_matsim_agg))

# compare municipality type matching
print("Comparing municipality type matching...")
print("Correctly matched municipality types:", np.sum(df_trips_matsim_agg["municipality_type"].values == df_trips_matsim_agg["municipality_type_beddem"].values) / len(df_trips_matsim_agg))
print("Incorrectly matched municipality types:",np.sum(df_trips_matsim_agg["municipality_type"].values != df_trips_matsim_agg["municipality_type_beddem"].values) / len(df_trips_matsim_agg))

# # Vehicle stocks
print("--- VEHICLE STOCKS ---")

# matsim vehicle stock
print("Getting MATSim vehicle stock...")
df_vehicle_stock_matsim = (df_trips_matsim_agg[["vehicle_type", "powertrain"]]
                           .groupby(["vehicle_type", "powertrain"])
                           .size()
                           .reset_index()
                           .rename(columns={0: "count"})
                           )
print(df_vehicle_stock_matsim.head(3))

# beddem stock for agents using car
print("Getting BEDDEM vehicle stock...")
df_vehicle_stock_beddem = (df_agents_beddem[["vehicle_type", "powertrain", "weight"]]
                           .groupby(["vehicle_type", "powertrain"])
                           .sum()
                           .reset_index()
                           .rename(columns={"weight": "count"})
                           )
print(df_vehicle_stock_beddem.head(3))

# compare vehicle stocks
print("Comparing vehicle stocks...")
df_vehicle_stock_compare = pd.merge(df_vehicle_stock_matsim, df_vehicle_stock_beddem,
                                    on=["vehicle_type", "powertrain"],
                                    how="outer",
                                    suffixes=["_matsim", "_beddem"]).fillna(0.0)
df_vehicle_stock_compare["count_matsim"] = df_vehicle_stock_compare["count_matsim"] / np.sum(df_vehicle_stock_compare["count_matsim"])
df_vehicle_stock_compare["count_beddem"] = df_vehicle_stock_compare["count_beddem"] / np.sum(df_vehicle_stock_compare["count_beddem"])

a = df_vehicle_stock_compare.rename({"count_matsim": "share"}, axis=1).drop("count_beddem", axis=1)
b = df_vehicle_stock_compare.rename({"count_beddem": "share"}, axis=1).drop("count_matsim", axis=1)

a["case"] = "matsim"
b["case"] = "beddem"

df_vehicle_stock_compare = pd.concat([a, b])

sns.set(style="whitegrid")
ax1 = sns.catplot(x="powertrain", y="share",
                  hue="case",
                  col="vehicle_type",
                  kind="bar",
                  data=df_vehicle_stock_compare)

print("Plotting results...")
ax1.savefig('{dir}/vehicle_stock_comparison.{ext}'.format(dir=options.fig_dir, ext=options.fig_ext))


# # Generating output for Swissmod
print("--- SWISSMOD ---")
print("Generating output for Swissmod...")

# merge vehicle info into matsim car trips
print("Merging agent vehicle info into MATSim car trips...")
df_matsim_agent_veh = df_trips_matsim_agg[["person_id", "vehicle_type", "powertrain", "consumption"]]
df_trips_w_veh = pd.merge(df_trips_car, df_matsim_agent_veh, on="person_id")

# get end times
print("Getting trip end times...")
df_trips_w_veh.loc[:,"endTime"] = df_trips_w_veh.loc[:,"start_time"] + df_trips_w_veh.loc[:,"travel_time"]

# rename columns
print("Renaming and cleaning column names...")
renames = {"person_id":"vehicleId",
           "vehicle_type":"vehicleType",
           "start_time":"startTime",
           "origin_x":"startX",
           "origin_y":"startY",
           "destination_x":"endX",
           "destination_y":"endY",
           "preceedingPurpose":"startActivityType",
           "followingPurpose":"endActivityType",
           "network_distance":"travelDistance_km"}
df_trips_w_veh = df_trips_w_veh.rename(index=str, columns=renames)

# only keep desired columns
df_trips_w_veh = df_trips_w_veh[["vehicleId",
                                 "vehicleType",
                                 "powertrain",
                                 "consumption",
                                 "startTime",
                                 "endTime",
                                 "startX",
                                 "startY",
                                 "endX",
                                 "endY",
                                 "startActivityType",
                                 "endActivityType",
                                 "travelDistance_km"]]

# set to desired format
print("Setting desired data types...")
df_trips_w_veh.loc[:, "vehicleId"] = df_trips_w_veh.loc[:, "vehicleId"].astype(int)
df_trips_w_veh.loc[:, "vehicleType"] = df_trips_w_veh.loc[:, "vehicleType"].astype(str)
df_trips_w_veh.loc[:, "powertrain"] = df_trips_w_veh.loc[:, "powertrain"].astype(str)
df_trips_w_veh.loc[:, "consumption"] = df_trips_w_veh.loc[:, "consumption"].astype(float)
df_trips_w_veh.loc[:, "startTime"] = df_trips_w_veh.loc[:, "startTime"].astype(float)
df_trips_w_veh.loc[:, "endTime"] = df_trips_w_veh.loc[:, "endTime"].astype(float)
df_trips_w_veh.loc[:, "startX"] = df_trips_w_veh.loc[:, "startX"].astype(float)
df_trips_w_veh.loc[:, "startY"] = df_trips_w_veh.loc[:, "startY"].astype(float)
df_trips_w_veh.loc[:, "endX"] = df_trips_w_veh.loc[:, "endX"].astype(float)
df_trips_w_veh.loc[:, "endY"] = df_trips_w_veh.loc[:, "endY"].astype(float)
df_trips_w_veh.loc[:, "startActivityType"] = df_trips_w_veh.loc[:, "startActivityType"].astype(str)
df_trips_w_veh.loc[:, "endActivityType"] = df_trips_w_veh.loc[:, "endActivityType"].astype(str)
df_trips_w_veh.loc[:, "travelDistance_km"] = df_trips_w_veh.loc[:, "travelDistance_km"].astype(float)

# sort by timestamp
print("Sorting data by timestamp...")
df_trips_w_veh = df_trips_w_veh.sort_values(by=["startTime","endTime"], ascending=True)
print(df_trips_w_veh.head(10))

# plot distance distribution
print("Plotting distance distribution...")
data = df_trips_w_veh["travelDistance_km"].values
plt.figure(dpi=120)
plt.hist(data, bins=500)
x_max = np.ceil(np.percentile(data, 95) / 10) * 10
plt.xlim((0, x_max))
plt.xlabel("Distance (km)")
plt.ylabel("# of car trips")
plt.savefig('{dir}/distance_distribution.{ext}'.format(dir=options.fig_dir, ext=options.fig_ext))

# save to file
print("Saving output...")
df_trips_w_veh.to_csv(options.output, sep=",", index=False)

print("Done")