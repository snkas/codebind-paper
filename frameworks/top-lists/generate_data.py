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

import sys
import os

from readhelpers import (
    # date_to_str,
    load_list,
    list_to_data_frame,
    summarize_each_column_into_statistic,
    AL0912_START,
    # AL0912_END,
    # AL1318_START,
    # AL1318_END,
    AL18_START,
    AL18_END ,
    UM1618_START,
    # UM1618_END,
    JOINT_START,
    JOINT_END
)


def write_to_data_file(data_frame, data_filename):
    with open(data_filename, "w+") as f_out:
        list_rank = list(data_frame.index.values)
        list_normed_statistics = list(data_frame.normed.values)
        for i in range(len(list_rank)):
            f_out.write("%d,%.6f\n" % (list_rank[i], list_normed_statistics[i]))


def plot_rank_against_daily_change_statistic(data_dir):

    # Create output directories
    os.makedirs(data_dir, exist_ok=True)

    # Return if the data is already complete
    if os.path.exists(data_dir + "/data-complete.txt"):
        with open(data_dir + "/data-complete.txt", "r") as f_data_complete:
            if f_data_complete.read().strip() == "Yes":
                print("The data is already complete, as such we do not generate it again.")
                return

    # The data set consists of the following series:
    list_alexa = load_list("alexa", AL0912_START, JOINT_END)
    list_umbrella = load_list("umbrella", UM1618_START, JOINT_END)
    list_majestic = load_list("majestic", JOINT_START, JOINT_END)

    # Converted into data frames:
    data_frame_alexa = list_to_data_frame("alexa", list_alexa)
    data_frame_umbrella = list_to_data_frame("umbrella", list_umbrella)
    data_frame_majestic = list_to_data_frame("majestic", list_majestic)

    # Go over all the statistics
    statistics = ["min", "mean", "median", "max"]
    for i in range(0, 100 + 1):
        statistics.append("percentile_%d" % i)
    i = 0
    for statistic in statistics:
        print("(%d/%d) Generating data for statistic %s..." % (i + 1, len(statistics), statistic))

        # Alexa_1318
        alexa_rank_to_daily_change_statistic_old = summarize_each_column_into_statistic(
            data_frame_alexa, AL0912_START, AL18_START, statistic
        )

        # Alexa_18
        alexa_rank_to_daily_change_statistic_new = summarize_each_column_into_statistic(
            data_frame_alexa, AL18_START, AL18_END, statistic
        )

        # Majestic_JOINT
        majestic_rank_to_daily_change_statistic_joint = summarize_each_column_into_statistic(
            data_frame_majestic, JOINT_START, JOINT_END, statistic
        )

        # Umbrella_JOINT
        umbrella_rank_to_daily_change_statistic_joint = summarize_each_column_into_statistic(
            data_frame_umbrella, JOINT_START, JOINT_END, statistic
        )

        # Write data files
        data_filename_alexa_old = data_dir + "/alexa_old_rank_against_" + statistic + ".csv"
        write_to_data_file(alexa_rank_to_daily_change_statistic_old, data_filename_alexa_old)
        data_filename_alexa_new = data_dir + "/alexa_new_rank_against_" + statistic + ".csv"
        write_to_data_file(alexa_rank_to_daily_change_statistic_new, data_filename_alexa_new)
        data_filename_majestic_joint = data_dir + "/majestic_joint_rank_against_" + statistic + ".csv"
        write_to_data_file(majestic_rank_to_daily_change_statistic_joint, data_filename_majestic_joint)
        data_filename_umbrella_joint = data_dir + "/umbrella_joint_rank_against_" + statistic + ".csv"
        write_to_data_file(umbrella_rank_to_daily_change_statistic_joint, data_filename_umbrella_joint)

        # Counter
        i = i + 1

    # The data is complete now
    with open(data_dir + "/data-complete.txt", "w+") as f_data_complete:
        f_data_complete.write("Yes")


def main():
    args = sys.argv[1:]
    if len(args) != 1:
        print("Must supply exactly two arguments")
        print("Usage: python3 generate_data.py [data_dir]")
        print("")
        exit(1)
    else:
        plot_rank_against_daily_change_statistic(args[0])


if __name__ == "__main__":
    main()
