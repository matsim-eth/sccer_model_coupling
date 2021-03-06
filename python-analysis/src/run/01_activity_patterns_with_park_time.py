import re
from bisect import bisect
from optparse import OptionParser

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

option_parser = OptionParser()
option_parser.add_option("-i", "--input", dest="input", help="features extracted by WriteSccerPlanFeatures")
option_parser.add_option("-f", "--figure", dest="figure", help="output path for figure file")
option_parser.add_option("-o", "--output", dest="output", help="output path for output csv")
options, args = option_parser.parse_args()

# Load in plan features
features = pd.read_csv(filepath_or_buffer=options.input, sep="\t")
features = features.query('longest_stop_s >= 0')
print(features.head(3))

# ## Meaningful clustering
# 
# Clustering based on meaningful boundaries.
# 
# First define some charging times.
# From https://www.clippercreek.com/wp-content/uploads/2016/04/TIME-TO-CHARGE-20170706_FINAL-LOW-RES.jpg,
# full charging times range from 2 to 70 hours depending on vehicle and charging station.

charge_time_thresholds = np.array([3600 * 2 ** i for i in range(1,10) if (2 ** i <= 24)])
print(charge_time_thresholds)


# Then define range.
# - Range of nissan leaf (most common EV): 135km https://en.wikipedia.org/wiki/Nissan_Leaf
# - Tesla 85D: 270 miles = 434km https://www.tesla.com/fr_CH/blog/driving-range-model-s-family?redirect=no
# 
# Range depends on lots of factors, so we just use a few thresholds starting at 50km up to 400km

range_thresholds = np.array([50 * 1000 * 2 ** i for i in range(4)])
print(range_thresholds / 1000)


# Now, just generate one label per combination and compute labels

def find_threshold(t, thresholds, unit):
    if t == len(thresholds):
        return ''.join(("> ", str(thresholds[t - 1]), unit))
    if t == 0:
        return ''.join(("[0 , ", str(thresholds[t]), unit, "]"))
    return ''.join(("[", str(thresholds[t - 1]), " , ", str(thresholds[t]), unit, "]"))


def comp_label(range_classes, charge_time_classes):
    m = map(lambda r, t: "".join(
        ("range_", find_threshold(r, range_thresholds / 1000, "km"),
         "-time_", find_threshold(t, charge_time_thresholds / 3600, "h"))),
            range_classes, charge_time_classes)
    return np.array(list(m))


pred_meaning = (features.assign(range_class=list(map(lambda x: bisect(range_thresholds, x), features.longest_trip_m)),
                                charge_time_class=list(map(lambda x: bisect(charge_time_thresholds, x), features.longest_stop_9_16_s)))
                .assign(range_label=lambda x: list(map(lambda t: find_threshold(t, range_thresholds / 1000, "km"), x.range_class)),
                        charge_time_label=lambda x: list(map(lambda t: find_threshold(t, charge_time_thresholds / 3600, "h"), x.charge_time_class)))
                .assign(label=lambda x: comp_label(x.range_class, x.charge_time_class)))
print(pred_meaning.head())

crosstab_clusters = pd.crosstab(pred_meaning.range_label, pred_meaning.charge_time_label)
print(crosstab_clusters)


# PSI wants to see when the cars are parked during the day.
# We should:
# - visualize the number of cars parked per TOD in a faceted way
# - export a table containing the number of parked car per time bin per class
# 

parked_columns = [v for v in pred_meaning.columns.values if v.startswith("parked_s")]


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


parktime_per_group = pred_meaning.groupby(("range_label", "charge_time_label"))[parked_columns].aggregate(np.average)
parktime_per_group['n'] = pred_meaning.groupby(("range_label", "charge_time_label"))['range_label'].aggregate(np.size)
parktime_per_group = parktime_per_group.reset_index()
parktime_per_group = pd.melt(parktime_per_group,
                             id_vars=['range_label', 'charge_time_label', 'n'], value_vars=parked_columns,
                             var_name="interval_s", value_name="parked_time_s"
                             )
parktime_per_group['interval_start_s'] = parktime_per_group["interval_s"].apply(decode_time('low'))
parktime_per_group['interval_end_s'] = parktime_per_group["interval_s"].apply(decode_time('high'))
parktime_per_group['time_of_day_s'] = parktime_per_group["interval_s"].apply(decode_time('middle'))
parktime_per_group['time_of_day_h'] = parktime_per_group['time_of_day_s'] / 3600.0
parktime_per_group['parked_time_min'] = parktime_per_group['parked_time_s'] / 60.0
parktime_per_group = parktime_per_group.drop(columns=['interval_s'])
print(parktime_per_group.head(10))

# To get nice plots: order categories in a meaningful way
print("Generating plots...")


def numeric_range(r):
    if r.startswith(">"): return float("inf")

    low = re.search("\[(.*),", r).group(1)
    return float(low)


# looks strange, but set cannot get a pandas series in constructor, while list can...
print("Ordering ranges...")
range_ordered = list(set(list(parktime_per_group.range_label)))
range_ordered.sort(key=numeric_range)
print(range_ordered)

print("Ordering parked times...")
charge_ordered = list(set(list(parktime_per_group.charge_time_label)))
charge_ordered.sort(key= numeric_range)
print(charge_ordered)


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

grid = sns.FacetGrid(parktime_per_group,
                      row="charge_time_label", col="range_label", hue="n",
                      row_order=charge_ordered, col_order=range_ordered,
                      palette=create_palette(parktime_per_group.n),
                      margin_titles=True)
grid.map(annotate, "n")
grid.map(plt.plot, "time_of_day_h", "parked_time_min")


# Save outputs
print("Saving outputs...")
print(options.figure)
grid.savefig(options.figure)
print(options.output)
parktime_per_group.to_csv(options.output)
print("Done")

