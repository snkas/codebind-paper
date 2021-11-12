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
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.ticker import FormatStrFormatter

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


def plot_rank_against_daily_change_statistic(pdf_dir):

    # Create output directories
    os.makedirs(pdf_dir, exist_ok=True)

    # Return if the figure already exists
    if os.path.exists(pdf_dir + "/plot_original_2c.pdf"):
        print("Figure is already present, not regenerating it.")
        return

    # The data set consists of the following series:
    list_alexa = load_list("alexa", AL0912_START, JOINT_END)
    list_umbrella = load_list("umbrella", UM1618_START, JOINT_END)
    list_majestic = load_list("majestic", JOINT_START, JOINT_END)

    data_frame_alexa = list_to_data_frame("alexa", list_alexa)
    data_frame_umbrella = list_to_data_frame("umbrella", list_umbrella)
    data_frame_majestic = list_to_data_frame("majestic", list_majestic)

    # Alexa_1318
    alexa_rank_to_daily_change_statistic_old = summarize_each_column_into_statistic(
        data_frame_alexa, AL0912_START, AL18_START, "mean"
    )

    # Alexa_18
    alexa_rank_to_daily_change_statistic_new = summarize_each_column_into_statistic(
        data_frame_alexa, AL18_START, AL18_END, "mean"
    )

    # Majestic_JOINT
    majestic_rank_to_daily_change_statistic_joint = summarize_each_column_into_statistic(
        data_frame_majestic, JOINT_START, JOINT_END, "mean"
    )

    # Umbrella_JOINT
    umbrella_rank_to_daily_change_statistic_joint = summarize_each_column_into_statistic(
        data_frame_umbrella, JOINT_START, JOINT_END, "mean"
    )

    # Original: matplotlib pyplot
    x = pd.DataFrame()
    x["Alexa_18"] = alexa_rank_to_daily_change_statistic_new.normed
    x["Umbrella_JOINT"] = umbrella_rank_to_daily_change_statistic_joint.normed
    x["Alexa_1318"] = alexa_rank_to_daily_change_statistic_old.normed
    x["Majestic_JOINT"] = majestic_rank_to_daily_change_statistic_joint.normed

    plt.rcParams.update({'font.size': 14})
    f, (ax, ax2) = plt.subplots(2, 1, sharex=True)  # Two plots
    f.tight_layout()
    f.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=None, hspace=None)

    # Ticks and spines
    ax.spines['bottom'].set_visible(False)  # Top plot no spine at the bottom
    ax.xaxis.tick_top()  # Add ticks at the top
    ax.tick_params(labeltop='off')  # No tick labels at the top
    ax2.spines['top'].set_visible(False)  # Bottom plot no spine at the top
    ax2.xaxis.tick_bottom()  # Add ticks at the bottom

    # The // on the left and right sides to indicate the axis break
    #
    d = .015  # how big to make the diagonal lines in axes coordinates
    # arguments to pass to plot, just so we don't keep repeating them
    kwargs = dict(transform=ax.transAxes, color='k', clip_on=False)
    ax.plot((-d, +d), (+d, -d), **kwargs)        # top-left diagonal
    ax.plot((1 + d, 1 - d), (-d, +d), **kwargs)  # top-right diagonal
    kwargs.update(transform=ax2.transAxes)  # switch to the bottom axes
    ax2.plot((-d, +d), (1.1 + d, 1.1 - d), **kwargs)  # bottom-left diagonal
    ax2.plot((1 - d, 1 + d), (1.1 + d, 1.1 - d), **kwargs)  # bottom-right diagonal

    # Plot the two lines
    styles = ['--', ':', '-', '-.']
    x[x.index > 100].plot(logx=True, ylim=[0.2, 10], ax=ax2, legend=False, style=styles)
    x[x.index > 100].plot(logx=True, ylim=[10, 50], ax=ax, logy=False, style=styles)

    plt.subplots_adjust(hspace=.001)  # Minor padding between subplots

    # Y-axis percentage as it is normalized
    ax.yaxis.set_major_formatter(FormatStrFormatter('%.0f%%'))
    ax2.yaxis.set_major_formatter(FormatStrFormatter('%.0f%%'))

    # Finally, save the figure as a PDF
    plt.savefig(pdf_dir + "/plot_original_2c.pdf", format='pdf', dpi=2000, bbox_inches='tight')
    # plt.show()


def main():
    args = sys.argv[1:]
    if len(args) != 1:
        print("Must supply exactly one argument")
        print("Usage: python3 plot_original.py [pdf_dir]")
        print("")
        print("     The output file will be: [pdf_dir]/plot_original_2c.pdf")
        print("")
        exit(1)
    else:
        plot_rank_against_daily_change_statistic(args[0])


if __name__ == "__main__":
    main()
