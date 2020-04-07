import re
from bisect import bisect
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
option_parser.add_option("--input", dest="input", help="features extracted by WriteSccerPlanFeatures")
option_parser.add_option("--mz-dir", dest="microcensus", help="microcensus data")
option_parser.add_option("--statpop-dir", dest="statpop", help="statpop data")
option_parser.add_option("--matsim-trips", dest="matsim_trips", help="MATSim trips")
option_parser.add_option("--municipality-shp", dest="mun_shp", help="Shapefile of Swiss municipalities")
option_parser.add_option("--spatial-structure", dest="spatial_structure", help="Swiss spatial structure data")
option_parser.add_option("--figure", dest="figure", help="output path for figure file")
option_parser.add_option("--output", dest="output", help="output path for output csv")
options, args = option_parser.parse_args()

mz_dir = options.microcensus
statpop_dir = options.statpop


# Load in plan features
features = pd.read_csv(filepath_or_buffer=options.input, sep="\t")
features = features.query('longest_stop_s >= 0')
print(features.head(3))
print("Features - number of agents", len(features["mzPersonId"]), len(features["mzPersonId"].unique()))

# ## Enrich data with microcensus data
#
# Add annual car km driven
df_mz_vehicles = (pd.read_csv("{dir}/fahrzeuge.csv".format(dir=mz_dir), encoding='latin')
                  .rename({"HHNR" : "mzPersonId",
                           "f30900_31700" : "year_km",
                           "f30700_hpnr1": "driver_1",
                           "f30700_hpnr2": "driver_2",
                           "f30700_hpnr3": "driver_3",
                           "f30700_hpnr4": "driver_4",
                           "f30700_hpnr5": "driver_5",
                           }, axis=1)
                  )[["mzPersonId", "year_km",
                     "driver_1", "driver_2", "driver_3", "driver_4", "driver_5"]]

print(df_mz_vehicles.head(3))
df_mz_vehicles["year_km"] = df_mz_vehicles["year_km"].replace([-97, -98, -99], -1)
df_mz_vehicles = df_mz_vehicles.replace([-97, -98, -99], 100)
df_mz_vehicles = (df_mz_vehicles
                  .sort_values(["driver_1", "driver_2", "driver_3", "driver_4", "driver_5"], ascending=True)
                  .groupby("mzPersonId", as_index=False).first()
                  )[["mzPersonId", "year_km"]]
print(df_mz_vehicles.head(3))

features = pd.merge(features, df_mz_vehicles, on='mzPersonId', how='left')
features = features.query("year_km >= 0")
print(features.head(3))
print("Vehicles - number of agents", len(df_mz_vehicles["mzPersonId"]), len(df_mz_vehicles["mzPersonId"].unique()))
print("Features - number of agents", len(features["mzPersonId"]), len(features["mzPersonId"].unique()))

# Add income info
df_mz_households = (pd.read_csv("{dir}/haushalte.csv".format(dir=mz_dir), encoding='latin')[["HHNR", "F20601"]]
                    .rename({"HHNR" : "mzPersonId",
                             "F20601" : "income"}, axis=1))
features = pd.merge(features, df_mz_households, on='mzPersonId', how='left')
features = features.query("income >= 0")
print(features.head(3))
print("Households - number of agents", len(df_mz_households["mzPersonId"]), len(df_mz_households["mzPersonId"].unique()))
print("Features - number of agents", len(features["mzPersonId"]), len(features["mzPersonId"].unique()))

# Add home location agglo type
df_trips_matsim = pd.read_csv(filepath_or_buffer=options.matsim_trips, sep=";")
df_trips_matsim = df_trips_matsim[~df_trips_matsim["person_id"].str.contains("freight")] # remove freight trips

# load municipality shapefile
print("Loading municipality shapefile...")
print(options.mun_shp)
df_municipalities = gpd.read_file(options.mun_shp, encoding = "latin1").to_crs('EPSG:2056')
df_municipalities = df_municipalities[["GMDNR", "geometry"]].rename({"GMDNR":"municipality_id"}, axis=1)
print(df_municipalities.head(3))

# load spatial structure data
print("Loading canton and municipality type data...")
print(options.spatial_structure)
df_municipality_types = pd.read_excel(options.spatial_structure,
                                      names=["municipality_id", "agglo_type"],
                                      usecols=[0, 17],
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
df_home = df_home[["person_id", "agglo_type"]]
df_home["person_id"] = df_home["person_id"].astype(np.int64)
df_home["agglo_type"] = df_home["agglo_type"].astype(int)
df_home = df_home.rename({"person_id": "agentId"}, axis=1)
print(df_home.head(3))

# merge spatial info
print("Merging home location info onto MATSim trips...")
features = pd.merge(features, df_home, on="agentId", how='left')
print(features.head(3))
print("Features - number of agents", len(features["mzPersonId"]), len(features["mzPersonId"].unique()))

# ## Meaningful clustering
#
# Clustering based on meaningful boundaries.
#
# First define annual car distances.

year_km_thresholds = np.array([11000, 20000])
print(year_km_thresholds)

# Now, just generate one label per combination and compute labels


def find_distance_label(t, thresholds, unit):
    if t == len(thresholds):
        return ''.join(("> ", str(thresholds[t - 1]), unit))
    if t == 0:
        return ''.join(("[0 , ", str(thresholds[t]), unit, "]"))
    return ''.join(("[", str(thresholds[t - 1]), " , ", str(thresholds[t]), unit, "]"))


def find_income_label(v):
    if v <= 5:
        return '<=10,000CHF'
    else:
        return '>10,000CHF'


def find_agglo_label(v):
    if v in [1, 2, 3, 4]:
        return 'urban'
    else:
        return 'rural'

def comp_label(annual_distance_km, income_levels, agglomeration_types):
    m = map(lambda d, i, a: "".join(
        ("distance_", find_distance_label(d, year_km_thresholds, "km"),
         "-income_", find_income_label(i),
         "-agglo_", find_agglo_label(a))),
            annual_distance_km, income_levels, agglomeration_types)
    return np.array(list(m))


pred_meaning = (features.assign(year_km_class=list(map(lambda x: bisect(year_km_thresholds, x), features.year_km)))
                .assign(year_km_label=lambda x: list(map(lambda t: find_distance_label(t, year_km_thresholds, "km"), x.year_km_class)),
                        income_label=lambda x: list(map(lambda t: find_income_label(t), x.income)),
                        agglo_label=lambda x: list(map(lambda t: find_agglo_label(t), x.agglo_type)))
                .assign(label=lambda x: comp_label(x.year_km_class, x.income, x.agglo_type)))
print(pred_meaning.head())

crosstab_clusters = pd.crosstab(pred_meaning.year_km_label, [pred_meaning.income_label, pred_meaning.agglo_label])
print(crosstab_clusters)


# PSI wants to see how much the cars are driven during the day.
# We should:
# - visualize the number of cars driving per TOD in a faceted way
# - export a table containing the number of driven cars per time bin per class
#

# print(list(pred_meaning.columns))

drive_columns = [v for v in pred_meaning.columns.values if v.startswith("driven_s")]
distance_columns = [v for v in pred_meaning.columns.values if v.startswith("distance_m")]

def decode_time(type):
    def f(name):
        interval = re.search("\[(.*)\]", name).group(1).split(';')

        low = float(interval[0])
        high = float(interval[1])

        if (type == 'middle'): return (low + high) / 2.0
        if (type == 'low'): return low
        if (type == 'high'): return high

        raise NameError(type)

    return f


# group by labels, average and count values
# melt according to driven time and distance

drivetime_per_group = pred_meaning.groupby(["year_km_label", "income_label", "agglo_label"])[drive_columns].aggregate(np.average)
drivetime_per_group['n'] = pred_meaning.groupby(["year_km_label", "income_label", "agglo_label"])["agglo_label"].agg(np.size)
drivetime_per_group = drivetime_per_group.reset_index()
drivetime_per_group = pd.melt(drivetime_per_group,
                              id_vars=['year_km_label', 'income_label', 'agglo_label', 'n'], value_vars=drive_columns,
                              var_name="interval_s", value_name="driven_time_s"
                              )
drivetime_per_group['interval_start_s'] = drivetime_per_group["interval_s"].apply(decode_time('low'))
drivetime_per_group['interval_end_s'] = drivetime_per_group["interval_s"].apply(decode_time('high'))
drivetime_per_group['time_of_day_s'] = drivetime_per_group["interval_s"].apply(decode_time('middle'))
drivetime_per_group['time_of_day_h'] = drivetime_per_group['time_of_day_s'] / 3600.0
drivetime_per_group['driven_time_min'] = drivetime_per_group['driven_time_s'] / 60.0
drivetime_per_group = drivetime_per_group.drop(columns=['interval_s'])
drivetime_per_group = drivetime_per_group.sort_values(['time_of_day_s', 'year_km_label', 'income_label', 'agglo_label'])

# distance per group
filter_list = distance_columns.copy()
filter_list.append("year_km")

distance_per_group = pred_meaning.groupby(["year_km_label", "income_label", "agglo_label"])[filter_list].aggregate(np.average)
distance_per_group['n'] = pred_meaning.groupby(["year_km_label", "income_label", "agglo_label"])["agglo_label"].agg(np.size)
distance_per_group = distance_per_group.reset_index()
distance_per_group = pd.melt(distance_per_group,
                             id_vars=['year_km_label', 'income_label', 'agglo_label', 'n', 'year_km'], value_vars=distance_columns,
                             var_name="interval_s", value_name="distance_m"
                             )
distance_per_group['time_of_day_s'] = distance_per_group["interval_s"].apply(decode_time('middle'))
distance_per_group['distance_km'] = distance_per_group['distance_m'] / 1000.0
distance_per_group = distance_per_group.drop(columns=['interval_s'])
distance_per_group = distance_per_group.sort_values(['time_of_day_s', 'year_km_label', 'income_label', 'agglo_label'])

assert len(drivetime_per_group) == len(distance_per_group)

# merge
results_per_group = pd.merge(drivetime_per_group, distance_per_group, on=['year_km_label', 'income_label', 'agglo_label', 'n', 'time_of_day_s'])
assert len(results_per_group) == len(distance_per_group)
results_per_group = results_per_group.sort_values(['time_of_day_s', 'year_km_label', 'income_label', 'agglo_label'])
print(results_per_group.head(30))


# To get nice plots: order categories in a meaningful way
print("Generating plots...")


def distance_range(r):
    if r.startswith(">"): return float("inf")

    low = re.search("\[(.*),", r).group(1)
    return float(low)

def income_agglo_range(r):
    code = ""
    if r.startswith(">") : code += "1"
    else : code += "0"

    if "urban" in r : code += "1"
    else : code += "0"

    return float(code)


# looks strange, but set cannot get a pandas series in constructor, while list can...
print("Ordering annual km traveled...")
distance_ordered = list(set(list(results_per_group.year_km_label)))
distance_ordered.sort(key=distance_range)
print(distance_ordered)

print("Ordering incomes + agglo types...")
results_per_group['income_agglo_label'] = results_per_group['income_label'].str.cat(results_per_group['agglo_label'], sep='\n')
income_agglo_ordered = list(set(list(results_per_group.income_agglo_label)))
income_agglo_ordered.sort(key=income_agglo_range)
print(income_agglo_ordered)


# Cannot get bloody Seaborn to understand that my "hue" variable should be continuous...
# Dirty hack to get this right
print("Generating figures...")


def create_palette(ns):
    my_palette = {}
    m = np.log(max(ns) + 2)
    all_blues = sns.color_palette("Blues", int(m) + 1)

    for n in ns:
        my_palette[n] = all_blues[int(np.log(n + 1))]

    return my_palette


def annotate(n, **kwargs):
    return plt.annotate("n=" + str(n.iloc[0]), xy=(0, 1))


plt.figure(dpi=120)
grid = sns.FacetGrid(results_per_group,
                     row="income_agglo_label", col="year_km_label", hue="n",
                     row_order=income_agglo_ordered, col_order=distance_ordered,
                     palette=create_palette(results_per_group.n),
                     margin_titles=True)
grid.map(annotate, "n")
grid.map(plt.plot, "time_of_day_h", "driven_time_min", color="b")
grid.map(plt.plot, "time_of_day_h", "distance_km", color="r")

# cleanup
results_per_group = results_per_group.drop(['income_agglo_label'], axis=1)[['year_km_label', 'income_label', 'agglo_label', 'n',
                                                                            'interval_start_s', 'interval_end_s', 'time_of_day_s', 'time_of_day_h',
                                                                            'driven_time_s', 'driven_time_min',
                                                                            'distance_m', 'distance_km', 'year_km']]

# Save outputs
print("Saving outputs...")
print(options.figure)
grid.savefig(options.figure)
print(options.output)
results_per_group.to_csv(options.output, sep=';', index=False)
print("Done")

