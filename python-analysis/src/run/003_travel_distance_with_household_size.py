import re
from bisect import bisect
from optparse import OptionParser

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

option_parser = OptionParser()
option_parser.add_option("--plans", type="string", dest="plans", help="features extracted by WriteSccerPlanFeatures")
option_parser.add_option("--households", dest="households", help="features extracted by WriteSccerHouseholdFeatures")
option_parser.add_option("--figure", dest="figure", help="output path for figure file")
option_parser.add_option("--output", dest="output", help="output path for output csv")
options, args = option_parser.parse_args()

# ## Loading features and merging
#
# Load basic features and additional household features and merge them.
print("Loading features and merging...")

plans = pd.read_csv(filepath_or_buffer=options.plans, sep="\t")
plans = plans.query('longest_stop_s >= 0')
households = pd.read_csv(filepath_or_buffer=options.households, sep="\t")
households = households.query('householdSize >= 0')
features = pd.merge(plans,households, on="agentId")
print(features.head(3))


# ## Meaningful clustering
#
# Clustering based on meaningful boundaries.
# We define driving ranges.
# - Range of nissan leaf (most common EV): 135km https://en.wikipedia.org/wiki/Nissan_Leaf
# - Tesla 85D: 270 miles = 434km https://www.tesla.com/fr_CH/blog/driving-range-model-s-family?redirect=no
#
# Range depends on lots of factors, so we just use a few thresholds starting at 50km up to 100km

print("Defining range clusters...")
range_thresholds = np.array([50 * 1000 * 2 ** i for i in range(2)])
print(range_thresholds / 1000)

# PSI is additionally interested in clustering according to household size.
# We therefore define three household types: single, couple and family.

print("Defining household clusters...")
household_thresholds = np.array([i + 1 for i in range(3)])
print(household_thresholds)

# Now, just generate one label per combination and compute labels

print("Adding labels...")


def find_threshold(t, thresholds, unit):
    if t == len(thresholds):
        return ''.join(("> ", str(thresholds[t - 1]), unit))
    if t == 0:
        return ''.join(("[0 , ", str(thresholds[t]), unit, "]"))
    return ''.join(("[", str(thresholds[t - 1]), " , ", str(thresholds[t]), unit, "]"))


def comp_label(range_classes, household_size_class):
    m = map(lambda r, s: "".join(
        ("range_", find_threshold(r,  range_thresholds / 1000, "km"),
         "-hhsize_", find_threshold(s, household_thresholds, ""))),
            range_classes, household_size_class)
    return np.array(list(m))


pred_meaning = (features.assign(range_class=list(map(lambda x: bisect(range_thresholds, x), features.longest_trip_m)),
                                household_size_class=list(map(lambda x: bisect(household_thresholds, x), features.householdSize)))
                .assign(range_label=lambda x: list(map(lambda t: find_threshold(t, range_thresholds / 1000, "km"), x.range_class)),
                        household_size_label=lambda x: list(map(lambda t: find_threshold(t, household_thresholds, ""), x.household_size_class)))
                .assign(label=lambda x: comp_label(x.range_class, x.household_size_class)))
print(pred_meaning.head())

crosstab_clusters = pd.crosstab(pred_meaning.range_label, pred_meaning.household_size_label)
print(crosstab_clusters)

# PSI wants to see when the cars are parked during the day.
# We should:
# - visualize the number of cars parked per TOD in a faceted way
# - export a table containing the number of parked car per time bin per class
#

print("Computing when cars park...")
parked_and_dist_columns = [v for v in pred_meaning.columns.values if (v.startswith("parked_s") or v.startswith("distance_m"))]


def decode_time(type):
    def f(name):
        interval = re.search("\[(.*)\]", name).group(1).split(';')

        low= float(interval[0])
        high=float(interval[1])

        if (type == 'middle'): return ( low + high ) / 2.0
        if (type == 'low'): return low
        if (type == 'high'): return high

        raise NameError(type)

    return f


parktime_per_group = pred_meaning.groupby(("range_label", "household_size_label"))[parked_and_dist_columns].aggregate( np.average )
parktime_per_group['n'] = pred_meaning.groupby(("range_label", "household_size_label"))['range_label'].aggregate( np.size )
parktime_per_group = parktime_per_group.reset_index()
parktime_per_group = pd.melt( parktime_per_group,
                              id_vars=['range_label', 'household_size_label', 'n'], value_vars=parked_and_dist_columns,
                              var_name="variable", value_name="value")
parktime_per_group['interval_start_s'] = parktime_per_group["variable"].apply( decode_time('low'))
parktime_per_group['interval_end_s'] = parktime_per_group["variable"].apply( decode_time('high'))
parktime_per_group['time_of_day_s'] = parktime_per_group["variable"].apply( decode_time('middle'))
parktime_per_group['variable'] = parktime_per_group['variable'].apply(lambda s: re.search('(.*)_\[.*\]', s).group(1))

parktime_per_group = parktime_per_group.set_index([c for c in parktime_per_group.columns.values if c != 'value']) \
    .unstack('variable').reset_index()
parktime_per_group.columns = [' '.join(c).strip().split(' ')[-1] for c in parktime_per_group.columns]
parktime_per_group['time_of_day_h'] = parktime_per_group['time_of_day_s'] / 3600.0
parktime_per_group['parked_time_min'] = parktime_per_group['parked_s'] / 60.0
parktime_per_group['distance_km'] = parktime_per_group['distance_m'] / 1000.0
#parktime_per_group = parktime_per_group.drop(columns=['interval_s'])
print(parktime_per_group)

# To get nice plots: order categories in a meaningful way
print("Setting up plots...")


def numeric_range(r):
    if r.startswith(">"): return float("inf")

    low = re.search("\[(.*),", r).group(1)
    return float(low)


# looks strange, but set cannot get a pandas series in constructor, while list can...
print("Ordering parked times...")
range_ordered = list(set(list(parktime_per_group.range_label)))
range_ordered.sort(key=numeric_range)
print(range_ordered)

print("Ordering household sizes...")
household_size_ordered = list(set(list(parktime_per_group.household_size_label)))
household_size_ordered.sort(key= numeric_range)
print(household_size_ordered)


# # In[17]:
#
#
#
# n_levels = sorted( set( list( parktime_per_group.n ) ) )
#
#
# # In[34]:


# Cannot get bloody Seaborn to understand that my "hue" variable should be continuous...
# Dirty hack to get this right
print("Generating figures...")
def create_palette(ns):
    my_palette = {}
    m = np.log(max(ns) + 2)
    all_blues = sns.color_palette("Blues", int(m) + 1 )

    for n in ns:
        my_palette[n] = all_blues[int(np.log(n + 1))]

    return my_palette

def annotate(n, **kwargs):
    return plt.annotate("n=" + str(n.iloc[0]), xy=(0,1))

# plot
grid = sns.FacetGrid(parktime_per_group,
                     row="household_size_label", col="range_label", hue="n",
                     row_order=household_size_ordered, col_order=range_ordered,
                     palette=create_palette(parktime_per_group.n),
                     margin_titles=True)
grid.map(annotate, "n")
grid.map(plt.plot, "time_of_day_h", "parked_time_min")

grid_d = sns.FacetGrid(parktime_per_group,
                       row="household_size_label", col="range_label", hue="n",
                       row_order=household_size_ordered, col_order=range_ordered,
                       palette=create_palette(parktime_per_group.n),
                       margin_titles=True)
grid_d.map(annotate, "n")
grid_d.map(plt.plot, "time_of_day_h", "distance_km")


print("Saving output...")
grid.savefig( options.figure )
parktime_per_group.to_csv( options.output )
