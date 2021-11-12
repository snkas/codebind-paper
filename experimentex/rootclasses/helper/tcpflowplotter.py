# The MIT License (MIT)
#
# Copyright (c) 2021 ETH Zurich
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import math
import numpy as np
import exputil


def generate_tcp_flow_rate_csv(logs_ns3_dir, data_out_dir, tcp_flow_id, interval_ns):

    # Read in CSV of the progress
    progress_csv_columns = exputil.read_csv_direct_in_columns(
        logs_ns3_dir + "/tcp_flow_" + str(tcp_flow_id) + "_progress.csv",
        "pos_int,pos_int,pos_int"
    )
    num_entries = len(progress_csv_columns[0])
    tcp_flow_id_list = progress_csv_columns[0]
    time_ns_list = progress_csv_columns[1]
    progress_byte_list = progress_csv_columns[2]

    # TCP Flow ID list must be all exactly tcp_flow_id
    for i in tcp_flow_id_list:
        if i != tcp_flow_id:
            raise ValueError("The flow identifier does not match (it must be the same in the entire progress file)")

    # Add up all the progress made in that interval
    current_interval = (0, interval_ns, 0)
    intervals = []
    last_progress_byte = 0
    for i in range(num_entries):

        # Continue to fast-forward intervals until the next entry is in it
        while time_ns_list[i] >= current_interval[1]:
            intervals.append(current_interval)
            current_interval = (current_interval[1], current_interval[1] + interval_ns, 0)

        # Now it must be within current_interval
        current_interval = (
            current_interval[0],
            current_interval[1],
            current_interval[2] + progress_byte_list[i] - last_progress_byte
        )
        last_progress_byte = progress_byte_list[i]

    # Add the last interval if it is not empty
    if current_interval[2] != 0:
        intervals.append(current_interval)

    # Now go over the intervals
    #
    # Each interval [a, b] with progress c, gets converted into two points:
    # a, c
    # b - (small number), c
    #
    # This effectively creates a step function as a continuous line, which can then be plotted by gnuplot.
    #
    data_filename = data_out_dir + "/tcp_flow_" + str(tcp_flow_id) + "_rate_in_intervals.csv"
    with open(data_filename, "w+") as f_out:
        for i in range(len(intervals)):
            rate_megabit_per_s = intervals[i][2] / 125000.0 * (1e9 / interval_ns)
            f_out.write("%d,%.6f,%.6f\n" % (tcp_flow_id, intervals[i][0], rate_megabit_per_s))
            # The last ending one can end exact
            if i == len(intervals) - 1:
                f_out.write("%d,%.6f,%.6f\n" % (tcp_flow_id, intervals[i][1], rate_megabit_per_s))
            else:
                f_out.write("%d,%.6f,%.6f\n" % (tcp_flow_id, intervals[i][1] - 0.00001, rate_megabit_per_s))

    # Show what is produced
    print("Interval: " + str(interval_ns / 1000000.0) + " ms")
    print("Line format: [tcp_flow_id],[time_moment_ns],[rate in Mbps]")
    print("Produced: " + data_filename)


def plot_tcp_flow(logs_ns3_dir, plt_dir, data_out_dir, pdf_out_dir, tcp_flow_id, interval_ns, segment_size_byte):
    local_shell = exputil.LocalShell()

    # Check that all plotting files are available
    if not local_shell.file_exists(plt_dir + "/" + "plot_tcp_flow_time_vs_cwnd.plt") or \
            not local_shell.file_exists(plt_dir + "/" + "plot_tcp_flow_time_vs_progress.plt") or \
            not local_shell.file_exists(plt_dir + "/" + "plot_tcp_flow_time_vs_rtt.plt") or \
            not local_shell.file_exists(plt_dir + "/" + "plot_tcp_flow_time_vs_rate.plt"):
        print("The gnuplot files are not present.")
        print("Are you executing this python file inside the plot_tcp_flow directory?")
        exit(1)

    # Create the output directories if they don't exist yet
    local_shell.make_full_dir(data_out_dir)
    local_shell.make_full_dir(pdf_out_dir)

    # Create rate file
    generate_tcp_flow_rate_csv(logs_ns3_dir, data_out_dir, tcp_flow_id, interval_ns)

    # Plot time vs. rate
    data_filename = data_out_dir + "/tcp_flow_" + str(tcp_flow_id) + "_rate_in_intervals.csv"
    pdf_filename = pdf_out_dir + "/plot_tcp_flow_time_vs_rate_" + str(tcp_flow_id) + ".pdf"
    plt_filename = plt_dir + "/" + "plot_tcp_flow_time_vs_rate.plt"
    local_shell.copy_file(plt_filename, "temp.plt")
    local_shell.sed_replace_in_file_plain("temp.plt", "[OUTPUT-FILE]", pdf_filename)
    local_shell.sed_replace_in_file_plain("temp.plt", "[DATA-FILE]", data_filename)
    local_shell.perfect_exec("gnuplot temp.plt")
    print("Produced plot: " + pdf_filename)
    local_shell.remove("temp.plt")

    # Plot time vs. progress
    data_filename = logs_ns3_dir + "/tcp_flow_" + str(tcp_flow_id) + "_progress.csv"
    local_shell.copy_file(data_filename, data_out_dir + "/tcp_flow_" + str(tcp_flow_id) + "_progress.csv")
    pdf_filename = pdf_out_dir + "/plot_tcp_flow_time_vs_progress_" + str(tcp_flow_id) + ".pdf"
    plt_filename = plt_dir + "/" + "plot_tcp_flow_time_vs_progress.plt"
    local_shell.copy_file(plt_filename, "temp.plt")
    local_shell.sed_replace_in_file_plain("temp.plt", "[OUTPUT-FILE]", pdf_filename)
    local_shell.sed_replace_in_file_plain("temp.plt", "[DATA-FILE]", data_filename)
    local_shell.perfect_exec("gnuplot temp.plt")
    print("Produced plot: " + pdf_filename)
    local_shell.remove("temp.plt")

    # Plot time vs. rtt
    data_filename = logs_ns3_dir + "/tcp_flow_" + str(tcp_flow_id) + "_rtt.csv"
    local_shell.copy_file(data_filename, data_out_dir + "/tcp_flow_" + str(tcp_flow_id) + "_rtt.csv")
    pdf_filename = pdf_out_dir + "/plot_tcp_flow_time_vs_rtt_" + str(tcp_flow_id) + ".pdf"
    plt_filename = plt_dir + "/" + "plot_tcp_flow_time_vs_rtt.plt"
    local_shell.copy_file(plt_filename, "temp.plt")
    local_shell.sed_replace_in_file_plain("temp.plt", "[OUTPUT-FILE]", pdf_filename)
    local_shell.sed_replace_in_file_plain("temp.plt", "[DATA-FILE]", data_filename)
    local_shell.perfect_exec("gnuplot temp.plt")
    print("Produced plot: " + pdf_filename)
    local_shell.remove("temp.plt")

    # Plot time vs. rto
    data_filename = logs_ns3_dir + "/tcp_flow_" + str(tcp_flow_id) + "_rto.csv"
    local_shell.copy_file(data_filename, data_out_dir + "/tcp_flow_" + str(tcp_flow_id) + "_rto.csv")
    pdf_filename = pdf_out_dir + "/plot_tcp_flow_time_vs_rto_" + str(tcp_flow_id) + ".pdf"
    plt_filename = plt_dir + "/" + "plot_tcp_flow_time_vs_rto.plt"
    local_shell.copy_file(plt_filename, "temp.plt")
    local_shell.sed_replace_in_file_plain("temp.plt", "[OUTPUT-FILE]", pdf_filename)
    local_shell.sed_replace_in_file_plain("temp.plt", "[DATA-FILE]", data_filename)
    local_shell.perfect_exec("gnuplot temp.plt")
    print("Produced plot: " + pdf_filename)
    local_shell.remove("temp.plt")

    # Plot time vs. cwnd
    data_filename = logs_ns3_dir + "/tcp_flow_" + str(tcp_flow_id) + "_cwnd.csv"
    local_shell.copy_file(data_filename, data_out_dir + "/tcp_flow_" + str(tcp_flow_id) + "_cwnd.csv")
    pdf_filename = pdf_out_dir + "/plot_tcp_flow_time_vs_cwnd_" + str(tcp_flow_id) + ".pdf"
    plt_filename = plt_dir + "/" + "plot_tcp_flow_time_vs_cwnd.plt"
    local_shell.copy_file(plt_filename, "temp.plt")
    local_shell.sed_replace_in_file_plain("temp.plt", "[OUTPUT-FILE]", pdf_filename)
    local_shell.sed_replace_in_file_plain("temp.plt", "[SEGMENT-SIZE-BYTE]", str(float(segment_size_byte)))
    local_shell.sed_replace_in_file_plain("temp.plt", "[DATA-FILE]", data_filename)
    local_shell.perfect_exec("gnuplot temp.plt")
    print("Produced plot: " + pdf_filename)
    local_shell.remove("temp.plt")

    # Plot time vs. cwnd_inflated
    data_filename = logs_ns3_dir + "/tcp_flow_" + str(tcp_flow_id) + "_cwnd_inflated.csv"
    local_shell.copy_file(data_filename, data_out_dir + "/tcp_flow_" + str(tcp_flow_id) + "_cwnd_inflated.csv")
    pdf_filename = pdf_out_dir + "/plot_tcp_flow_time_vs_cwnd_inflated_" + str(tcp_flow_id) + ".pdf"
    plt_filename = plt_dir + "/" + "plot_tcp_flow_time_vs_cwnd_inflated.plt"
    local_shell.copy_file(plt_filename, "temp.plt")
    local_shell.sed_replace_in_file_plain("temp.plt", "[OUTPUT-FILE]", pdf_filename)
    local_shell.sed_replace_in_file_plain("temp.plt", "[SEGMENT-SIZE-BYTE]", str(float(segment_size_byte)))
    local_shell.sed_replace_in_file_plain("temp.plt", "[DATA-FILE]", data_filename)
    local_shell.perfect_exec("gnuplot temp.plt")
    print("Produced plot: " + pdf_filename)
    local_shell.remove("temp.plt")

    # Plot time vs. ssthresh
    data_filename = logs_ns3_dir + "/tcp_flow_" + str(tcp_flow_id) + "_ssthresh.csv"

    # Retrieve the highest ssthresh which is not a max. integer
    ssthresh_values = exputil.read_csv_direct_in_columns(data_filename, "pos_int,pos_int,pos_int")[2]
    max_ssthresh = 0
    for ssthresh in ssthresh_values:
        if ssthresh > max_ssthresh and ssthresh != 4294967295:
            max_ssthresh = ssthresh
    if max_ssthresh == 0:  # If it never got out of initial slow-start, we just set it to 1 for the plot
        max_ssthresh = 1.0

    # Execute ssthresh plotting
    local_shell.copy_file(data_filename, data_out_dir + "/tcp_flow_" + str(tcp_flow_id) + "_ssthresh.csv")
    pdf_filename = pdf_out_dir + "/plot_tcp_flow_time_vs_ssthresh_" + str(tcp_flow_id) + ".pdf"
    plt_filename = plt_dir + "/" + "plot_tcp_flow_time_vs_ssthresh.plt"
    local_shell.copy_file(plt_filename, "temp.plt")
    local_shell.sed_replace_in_file_plain(
        "temp.plt",
        "[MAX-Y]",
        str(math.ceil(max_ssthresh / float(segment_size_byte)))
    )
    local_shell.sed_replace_in_file_plain("temp.plt", "[OUTPUT-FILE]", pdf_filename)
    local_shell.sed_replace_in_file_plain("temp.plt", "[SEGMENT-SIZE-BYTE]", str(float(segment_size_byte)))
    local_shell.sed_replace_in_file_plain("temp.plt", "[DATA-FILE]", data_filename)
    local_shell.perfect_exec("gnuplot temp.plt")
    print("Produced plot: " + pdf_filename)
    local_shell.remove("temp.plt")

    # Plot time vs. inflight
    data_filename = logs_ns3_dir + "/tcp_flow_" + str(tcp_flow_id) + "_inflight.csv"
    local_shell.copy_file(data_filename, data_out_dir + "/tcp_flow_" + str(tcp_flow_id) + "_inflight.csv")
    pdf_filename = pdf_out_dir + "/plot_tcp_flow_time_vs_inflight_" + str(tcp_flow_id) + ".pdf"
    plt_filename = plt_dir + "/" + "plot_tcp_flow_time_vs_inflight.plt"
    local_shell.copy_file(plt_filename, "temp.plt")
    local_shell.sed_replace_in_file_plain("temp.plt", "[OUTPUT-FILE]", pdf_filename)
    local_shell.sed_replace_in_file_plain("temp.plt", "[SEGMENT-SIZE-BYTE]", str(float(segment_size_byte)))
    local_shell.sed_replace_in_file_plain("temp.plt", "[DATA-FILE]", data_filename)
    local_shell.perfect_exec("gnuplot temp.plt")
    print("Produced plot: " + pdf_filename)
    local_shell.remove("temp.plt")

    # Plot time vs. together (cwnd, cwnd_inflated, ssthresh, inflight)
    cwnd_values = exputil.read_csv_direct_in_columns(
        logs_ns3_dir + "/tcp_flow_" + str(tcp_flow_id) + "_cwnd.csv", "pos_int,pos_int,pos_int")[2]
    cwnd_inflated_values = exputil.read_csv_direct_in_columns(
        logs_ns3_dir + "/tcp_flow_" + str(tcp_flow_id) + "_cwnd_inflated.csv", "pos_int,pos_int,pos_int")[2]
    pdf_filename = pdf_out_dir + "/plot_tcp_flow_time_vs_together_" + str(tcp_flow_id) + ".pdf"
    plt_filename = plt_dir + "/" + "plot_tcp_flow_time_vs_together.plt"
    local_shell.copy_file(plt_filename, "temp.plt")
    local_shell.sed_replace_in_file_plain("temp.plt", "[MAX-Y]", str(
        max(
            math.ceil(max_ssthresh / float(segment_size_byte)),
            math.ceil(np.max(cwnd_values) / float(segment_size_byte)),
            math.ceil(np.max(cwnd_inflated_values) / float(segment_size_byte))
        )
    ))
    local_shell.sed_replace_in_file_plain("temp.plt", "[OUTPUT-FILE]", pdf_filename)
    local_shell.sed_replace_in_file_plain("temp.plt", "[SEGMENT-SIZE-BYTE]", str(float(segment_size_byte)))
    local_shell.sed_replace_in_file_plain(
        "temp.plt", "[DATA-FILE-CWND]", logs_ns3_dir + "/tcp_flow_" + str(tcp_flow_id) + "_cwnd.csv"
    )
    local_shell.sed_replace_in_file_plain(
        "temp.plt", "[DATA-FILE-CWND-INFLATED]", logs_ns3_dir + "/tcp_flow_" + str(tcp_flow_id) + "_cwnd_inflated.csv"
    )
    local_shell.sed_replace_in_file_plain(
        "temp.plt", "[DATA-FILE-SSTHRESH]", logs_ns3_dir + "/tcp_flow_" + str(tcp_flow_id) + "_ssthresh.csv"
    )
    local_shell.perfect_exec("gnuplot temp.plt")
    print("Produced plot: " + pdf_filename)
    local_shell.remove("temp.plt")
