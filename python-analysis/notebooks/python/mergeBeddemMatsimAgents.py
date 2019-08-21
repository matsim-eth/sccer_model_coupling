import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import shapely.geometry as geo
import geopandas as gpd
from sklearn.neighbors import KDTree
from tqdm import tqdm

def to_gpd(df, x = "x", y = "y", crs = {"init" : "EPSG:2056"}):
    df["geometry"] = [
        geo.Point(*coord) for coord in tqdm(
            zip(df[x], df[y]), total = len(df),
            desc = "Converting coordinates"
        )]
    df = gpd.GeoDataFrame(df)
    df.crs = crs

    if not crs == {"init" : "EPSG:2056"}:
        df = df.to_crs({"init" : "EPSG:2056"})

    return df

def impute(df_points, df_zones, point_id_field, zone_id_field, fix_by_distance = True, chunk_size = 10000):
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
    for chunk in tqdm(np.array_split(df_points, chunk_count), total = chunk_count):
        result.append(gpd.sjoin(df_zones, chunk, op = "contains", how = "right"))
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
        indices = kd_tree.query(coordinates, return_distance = False).flatten()

        df_points.loc[invalid_mask, zone_id_field] = df_zones.iloc[indices][zone_id_field].values

    return pd.merge(df_original, df_points[[point_id_field, zone_id_field]], on = point_id_field, how = "left")


# load in vehicle stock (BEDDEM)
year = 2018
df_vehicles = pd.read_csv("/home/ctchervenkov/git/JA_Mobility_exchange/BEDDEM-MATSIM/01-disaggregatedvehiclestock." + str(year) + ".csv")
df_vehicles = df_vehicles.rename({"ID" : "agent_id",
                                  "Type_Of_Vehicle" : "vehicle_type",
                                  "Powertrain" : "powertrain",
                                  "Cons" : "consumption"}, axis=1)

df_vehicles = df_vehicles[["vehicle_type", "powertrain", "consumption", "CO2"]]
df_vehicles = df_vehicles.groupby(["vehicle_type", "powertrain"]).mean().reset_index()


# load in trips (BEDDEM)
year = 2018
df_trips = pd.read_csv("/home/ctchervenkov/git/JA_Mobility_exchange/BEDDEM-MATSIM/03-trips." + str(year) + ".csv")

# select only car trips
df_trips = df_trips[df_trips["Mode"] == "Car"].reset_index(drop=True)
df_trips = df_trips.rename({"AgentID" : "agent_id",
                            "gemeindetype" : "municipality_type",
                            "Kanton" : "canton",
                            "Vehicle_Category" : "vehicle_type",
                            "Vehicle_Type" : "powertrain",
                            "Day_Of_The_Week" : "day_of_week",
                            "Time_Start" : "time_start",
                            "Weather" : "weather",
                            "Mode" : "mode",
                            "Distance" : "distance",
                            "Purpose" : "purpose",
                            "Weight_To_Universe" : "weight"}, axis=1)

# merge vehicle info
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

# aggregate distance travelled by car (BEDDEM)
df_agents_beddem = df_trips_beddem.groupby(["agent_id",
                                            "municipality_type",
                                            "canton",
                                            "day_of_week",
                                            "vehicle_type",
                                            "powertrain",
                                            "consumption"]).agg({"distance" : "sum",
                                                                "weight" : "mean"}).reset_index()

df_agents_beddem = df_agents_beddem.groupby(["agent_id",
                                             "municipality_type",
                                             "canton",
                                             "vehicle_type",
                                             "powertrain",
                                             "consumption"]).agg({"distance" : "mean",
                                                                  "weight" : "mean"}).reset_index()

# load in trips (MATSim)
df_trips_matsim = pd.read_csv("/home/ctchervenkov/Documents/data/scenarios/switzerland_2018_10pct/output_trips.csv", sep=";")

# load municipality shapefile
shp = "/home/ctchervenkov/Documents/data/switzerland/data/municipality_borders/gd-b-00.03-875-gg18/ggg_2018-LV95/shp/g1g18.shp"
df_municipalities = gpd.read_file(shp, encoding = "latin1").to_crs({'init': 'EPSG:2056'})
df_municipalities = df_municipalities[["GMDNR", "geometry"]].rename({"GMDNR":"municipality_id"}, axis=1)

# load canton and municipality type data
df_municipality_types = pd.read_excel("/home/ctchervenkov/Documents/data/switzerland/data/spatial_structure_2018.xlsx",
                               names=["municipality_id", "canton_id", "municipality_type"],
                               usecols=[0, 2, 21],
                               skiprows=6,
                               nrows=2229,
                               )


# impute canton and municipality of agent's home location
df_home_matsim = df_trips_matsim[["person_id", "preceedingPurpose", "origin_x", "origin_y"]]
df_home_matsim = df_home_matsim[df_home_matsim["preceedingPurpose"] == "home"]
df_home_matsim = df_home_matsim.drop_duplicates().rename({"origin_x" : "x", "origin_y" : "y"}, axis=1)[["person_id", "x", "y"]]
df_home_matsim = to_gpd(df_home_matsim, "x", "y")
df_home_matsim = df_home_matsim.drop(["x", "y"], axis=1)
df_home = impute(df_home_matsim, df_municipalities, "person_id", "municipality_id")
df_home = pd.merge(df_home, df_municipality_types, on="municipality_id")
df_home = df_home[["person_id", "canton_id", "municipality_type"]]

# aggregate distance travelled by car (MATSim)
df_trips_matsim_agg = df_trips_matsim[df_trips_matsim["mode"] == "car"]
df_trips_matsim_agg = df_trips_matsim[["person_id",
                                       "network_distance"]
                                     ].groupby("person_id").agg({"network_distance" : "sum"}).reset_index()


# merge spatial info
df_trips_matsim_agg = pd.merge(df_trips_matsim_agg, df_home, on="person_id")
df_trips_matsim_agg = df_trips_matsim_agg.sort_values(["canton_id", "municipality_type"])

# for canton_id in df_trips_matsim_agg["canton_id"].unique():
for canton_id in [16]:
    print("canton", canton_id)
    df_trips_per_canton = df_trips_matsim_agg[df_trips_matsim_agg["canton_id"] == canton_id]

    #     for municipality_type in df_trips_per_canton["municipality_type"].unique():
    for municipality_type in [6]:
        print("municipality type", municipality_type)

        # get relevant MATSim agents
        df_trips_matsim_sub = df_trips_matsim_agg[(df_trips_matsim_agg["canton_id"] == canton_id) &
                                                  (df_trips_matsim_agg["municipality_type"] == municipality_type)]

        # get relevant BEDDEM agents
        df_agents_beddem_sub = df_agents_beddem

        print(df_agents_beddem_sub.head())

        if (canton_id in df_agents_beddem_sub["canton"]):
            df_agents_beddem_sub = df_agents_beddem_sub[df_agents_beddem_sub["canton"] == canton_id]

        print(df_agents_beddem_sub.head())

        if (municipality_type in df_agents_beddem_sub["municipality_type"]):
            df_agents_beddem_sub = df_agents_beddem_sub[df_agents_beddem_sub["municipality_type"] == municipality_type]

        print("Matching", len(df_trips_matsim_sub), "MATSim agents",
              "to", len(df_agents_beddem_sub), "relevant BEDDEM agents")

        # create KDtree from BEDDEM agents
        coordinates = np.vstack([df_agents_beddem_sub["distance"].values]).T
        kd_tree = KDTree(coordinates)

        # match MATSim agents
        matsim_pts = np.vstack([df_trips_matsim_sub["network_distance"].values]).T
        indices = kd_tree.query(matsim_pts, return_distance=False).flatten()
        df_matches = df_agents_beddem_sub.iloc[list(indices)]

    #         print(df_matches)

    #         df_trips_matsim_sub["vehicle_id"] = df_matches["vehicle_id"].values

    #         df_trips_matsim_agg.loc[df_trips_matsim_sub.index, "vehicle_id"] = df_trips_matsim_sub["vehicle_id"]

    print("---")
