# Based on code from (changes were made):
# Quirin Scheitle, Oliver Hohlfeld, Julien Gamba, Jonas Jelten,
# Torsten Zimmermann, Stephen D. Strowes, and Narseo Vallina-Rodriguez. 2018.
# A Long Way to the Top: Significance, Structure, and Stability of Internet Top Lists.
# In Proceedings of the Internet Measurement Conference 2018 (IMC '18). Association for
# Computing Machinery, New York, NY, USA, 478–493. DOI:https://doi.org/10.1145/3278532.3278574
# Original code can be found at: https://mediatum.ub.tum.de/1452290
#
# LICENSE
# by-sa, http://creativecommons.org/licenses/by-sa/4.0 (Attribution-ShareAlike 4.0 International)

import json
import datetime
import pandas as pd
from datetime import timedelta


# Alexa
# 2009-1-29 till 2012-3-16
# 2013-4-30 till 2018-1-28
# 2018-1-29 till 2018-4-30

AL0912_START = datetime.date(2009, 1, 29)
AL0912_END = datetime.date(2012, 3, 16)

AL1318_START = datetime.date(2013, 4, 30)
AL1318_END = datetime.date(2018, 1, 28)

AL18_START = datetime.date(2018, 1, 29)
AL18_END = datetime.date(2018, 4, 30)

# Umbrella
# 2016-12-15 till 2018-05-07

UM1618_START = datetime.date(2016, 12, 15)
UM1618_END = datetime.date(2018, 4, 30)

# Majestic
# 2017-06-06 till 2018-05-07

JOINT_START = datetime.date(2017, 6, 6)
JOINT_END = datetime.date(2018, 4, 30)


# Convert a date object to Y-m-d format
def date_to_str(dt):
    """
    Convert a date object to its Y-m-d string format.

    :param dt: Date object

    :return: Date as a string using Y-m-d format (e.g., 2017-01-03)
    """
    return dt.strftime("%Y-%m-%d")


def load_list(list_name, start_date_incl, end_date_incl):

    # Explanation
    print("Loading %s list" % list_name)
    print("  > Start date........... %s" % date_to_str(start_date_incl))
    print("  > End date............. %s" % date_to_str(end_date_incl))
    print("  > Expected # of days... %d" % ((end_date_incl - start_date_incl).days + 1))

    # For each date, save the time-deltas
    # Time-deltas are a dictionary from top-X to number of different
    #
    # For example:
    #
    # {
    #    1: 0,
    #    2: 1,
    #    ...
    #    900: 870
    #    ...
    #    1000000: 39000
    # }
    #
    # Which translates to:
    #
    # In the top-1, no difference
    # In the top-2, 1 difference
    # In the top-900, 870 difference
    # In the top-1M, 39000 difference
    #
    list_date_with_time_deltas = []

    for i in range((end_date_incl - start_date_incl).days + 1):

        # Calculate date
        dt = end_date_incl - timedelta(i)
        date_str = date_to_str(dt)

        # Read delta statistics of that day
        try:
            with open("analysis_qs_timedelta/" + list_name + "_" + date_str + ".json", "r") as f_in:
                stats = json.load(f_in)
        except FileNotFoundError:
            continue

        # Save time-deltas for that date
        list_date_with_time_deltas.append((pd.Timestamp(dt), stats["timedeltas"]))

    print("  > Actual # of days..... %d\n" % len(list_date_with_time_deltas))

    # Order from start to end instead of end to start
    list_date_with_time_deltas.reverse()

    # Return list
    return list_date_with_time_deltas


def list_to_data_frame(list_name, list_date_with_time_deltas):

    # Explanation
    print("Converting %s list to data frame..." % list_name)

    # Create a map for each date to its time-deltas
    # E.g.,
    # {
    # "2017-06-06" : { 1: 0, 2: 0, ..., 1000: 20, ..., 1000000: 6218 },
    # ...
    # }
    dict_date_to_time_deltas = {}
    for tuple_date_with_time_deltas in list_date_with_time_deltas:
        dict_date_to_time_deltas[tuple_date_with_time_deltas[0]] = tuple_date_with_time_deltas[1]

    # Now convert it into a data frame as follows:
    #                 1  2  3  ... 1000 ... 1000000
    # "2017-06-06"    0  0  1  ... 20   ... 6218
    #
    # The row indices are the dates, the columns are the K as in top-K considered
    dft = pd.DataFrame.from_dict(dict_date_to_time_deltas, orient="index")
    dft = dft.reindex(sorted(dft.columns, key=int), axis=1)

    # Finished
    print("  > # of rows...... %d" % (dft.shape[0]))
    print("  > # of columns... %d\n" % (dft.shape[1]))

    return dft


def summarize_each_column_into_statistic(dft, start_date, end_date, statistic):

    # Input is a data frame as follows:
    #                 1  2  3  ... 1000 ... 1000000
    # "2017-06-06"    0  0  1  ... 20   ... 6218

    # The goal is now for each column to get a summary statistic

    new_dft = dft[(dft.index > date_to_str(start_date)) & (dft.index < date_to_str(end_date))]
    if statistic == "mean":
        x = new_dft.mean().to_frame()
    elif statistic == "median":
        x = new_dft.median().to_frame()
    elif statistic == "min":
        x = new_dft.min().to_frame()
    elif statistic == "max":
        x = new_dft.max().to_frame()
    elif statistic.startswith("percentile_"):  # E.g., percentile_44
        quantile = float(statistic.split("_")[1]) / 100.0
        x = new_dft.quantile(quantile).to_frame()
    else:
        raise ValueError("Invalid statistic: " + statistic)
    x.index = x.index.astype('int')
    x.columns = ["raw"]
    x["normed"] = 100.0 * x.raw / x.index
    return x
