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

import os
import exputil
import numpy as np
import ast
import math


def gen_basic_sim_tcp_flows_plot_data(experiment_plot_dir, data_path, list_run_dir, flow_groups_name_and_size):

    # Create the output directories if they don't exist yet
    data_dir = experiment_plot_dir + "/" + data_path
    os.makedirs(data_dir, exist_ok=True)

    # Collect the statistics
    list_target_load_percentage_with_run_no = []
    statistics = {}
    for run_dir in list_run_dir:

        # Currently working on
        logs_ns3_dir = run_dir + "/logs_ns3"
        print("Handling run: " + run_dir)

        # We evaluate the different runs for each flow arrival rate
        with open(run_dir + "/data-structure.txt", "r") as f_in:
            run_data_structure = ast.literal_eval(f_in.read())
            target_load_percentage = run_data_structure["load_with_lambda_flow_arrival_rate"][1][0]
            expected_flows_per_s = run_data_structure["load_with_lambda_flow_arrival_rate"][1][1]
            run_no = run_data_structure["run_number"][1]
            list_target_load_percentage_with_run_no.append((target_load_percentage, run_no))
            total_expected_num_flows = run_data_structure["total_expected_num_flows"][1]
            duration_ns = int(math.ceil(float(total_expected_num_flows) / float(expected_flows_per_s) * 1000000000))
            warm_up_ns = run_data_structure["warm_up_ns"][1]
            cool_down_ns = run_data_structure["cool_down_ns"][1]
            duration_ns += warm_up_ns + cool_down_ns

        # Create rate file
        tcp_flows_csv_columns = exputil.read_csv_direct_in_columns(
            logs_ns3_dir + "/tcp_flows.csv",
            "idx_int,pos_int,pos_int,pos_int,pos_int,pos_int,pos_int,pos_int,string,string"
        )
        total_num_flows = len(tcp_flows_csv_columns[0])
        # flow_id_list = tcp_flows_csv_columns[0]
        # from_node_id_list = tcp_flows_csv_columns[1]
        # to_node_id_list = tcp_flows_csv_columns[2]
        size_byte_list = tcp_flows_csv_columns[3]
        start_time_ns_list = tcp_flows_csv_columns[4]
        # end_time_ns_list = tcp_flows_csv_columns[5]
        duration_ns_list = tcp_flows_csv_columns[6]
        # amount_sent_byte_list = tcp_flows_csv_columns[7]
        finished_list = tcp_flows_csv_columns[8]
        # metadata_list = tcp_flows_csv_columns[9]

        # Process flows and put them into their respective groups
        interval_num_flows = 0
        interval_completed_flows = []
        interval_per_group_num_flows = []
        interval_per_group_completed_flows = []
        for g in range(len(flow_groups_name_and_size)):
            interval_per_group_num_flows.append(0)
            interval_per_group_completed_flows.append([])
        for i in range(total_num_flows):
            if warm_up_ns <= start_time_ns_list[i] < duration_ns - cool_down_ns:

                # Whether the TCP flow is finished
                is_completed = finished_list[i] == "YES"

                # Flow size group it belongs to
                chosen_g = -1
                for g in range(len(flow_groups_name_and_size)):
                    if size_byte_list[i] == flow_groups_name_and_size[g][1]:
                        chosen_g = g
                        break
                if chosen_g == -1:
                    raise ValueError("Flow does not belong to any group: should not happen")

                # Update total amount of flows per group, whether they are finished or not
                interval_per_group_num_flows[chosen_g] += 1
                interval_num_flows += 1

                # Only if completed are they taken into account for the statistics
                if is_completed:
                    info_tuple = (
                        i,  # TCP flow identifier
                        duration_ns_list[i],  # Duration in ns
                        float(size_byte_list[i]) / float(duration_ns_list[i]) * 8000.0  # Rate in Mbit/s
                    )
                    interval_completed_flows.append(info_tuple)
                    interval_per_group_completed_flows[chosen_g].append(info_tuple)

        # Print information for checking
        print("Collected flows:")
        print("  > %d out of %d flows were in the measurement interval" % (interval_num_flows, total_num_flows))
        print("  > Within the interval:")
        print("    >> All flows...... %d/%d completed" % (len(interval_completed_flows), interval_num_flows))
        for g in range(len(flow_groups_name_and_size)):
            print("    >> %s flows...... %d/%d completed" % (
                flow_groups_name_and_size[g][0],
                len(interval_per_group_completed_flows[g]),
                interval_per_group_num_flows[g]
            ))

        # All statistics groups (incl. all)
        statistic_groups = []
        for g in range(len(flow_groups_name_and_size)):
            statistic_groups.append(
                (flow_groups_name_and_size[g][0], interval_per_group_completed_flows[g], interval_per_group_num_flows[g])
            )
        statistic_groups.append(
            ("all", interval_completed_flows, interval_num_flows)
        )

        # Calculate the statistics we want
        for statistic_group in statistic_groups:

            # Extract what we need for the statistics
            group_name = statistic_group[0]
            info_list = statistic_group[1]
            total_including_non_completed = statistic_group[2]
            fct_ns_list = list(map(lambda x: x[1], info_list))
            avg_throughput_megabit_per_s_list = list(map(lambda x: x[2], info_list))

            # If not enough flows were completed
            statistics[(target_load_percentage, run_no, group_name, "fraction_completed")] = float(len(info_list)) / float(total_including_non_completed)

            # FCT statistics
            statistics[(target_load_percentage, run_no, group_name, "fct_ns_min")] = np.min(fct_ns_list)
            statistics[(target_load_percentage, run_no, group_name, "fct_ns_0_1th_percentile")] = np.percentile(fct_ns_list, 0.1)
            statistics[(target_load_percentage, run_no, group_name, "fct_ns_1th_percentile")] = np.percentile(fct_ns_list, 1.0)
            statistics[(target_load_percentage, run_no, group_name, "fct_ns_10th_percentile")] = np.percentile(fct_ns_list, 10.0)
            statistics[(target_load_percentage, run_no, group_name, "fct_ns_25th_percentile")] = np.percentile(fct_ns_list, 25.0)
            statistics[(target_load_percentage, run_no, group_name, "fct_ns_average")] = np.mean(fct_ns_list)
            statistics[(target_load_percentage, run_no, group_name, "fct_ns_median")] = np.median(fct_ns_list)
            statistics[(target_load_percentage, run_no, group_name, "fct_ns_75th_percentile")] = np.percentile(fct_ns_list, 75.0)
            statistics[(target_load_percentage, run_no, group_name, "fct_ns_90th_percentile")] = np.percentile(fct_ns_list, 90.0)
            statistics[(target_load_percentage, run_no, group_name, "fct_ns_99th_percentile")] = np.percentile(fct_ns_list, 99.0)
            statistics[(target_load_percentage, run_no, group_name, "fct_ns_99_9th_percentile")] = np.percentile(fct_ns_list, 99.9)
            statistics[(target_load_percentage, run_no, group_name, "fct_ns_max")] = np.max(fct_ns_list)

            # Average throughput statistics
            statistics[(target_load_percentage, run_no, group_name, "avg_throughput_megabit_per_s_min")] = np.min(avg_throughput_megabit_per_s_list)
            statistics[(target_load_percentage, run_no, group_name, "avg_throughput_megabit_per_s_0_1th_percentile")] = np.percentile(avg_throughput_megabit_per_s_list, 0.1)
            statistics[(target_load_percentage, run_no, group_name, "avg_throughput_megabit_per_s_1th_percentile")] = np.percentile(avg_throughput_megabit_per_s_list, 1.0)
            statistics[(target_load_percentage, run_no, group_name, "avg_throughput_megabit_per_s_10th_percentile")] = np.percentile(avg_throughput_megabit_per_s_list, 10.0)
            statistics[(target_load_percentage, run_no, group_name, "avg_throughput_megabit_per_s_25th_percentile")] = np.percentile(avg_throughput_megabit_per_s_list, 25.0)
            statistics[(target_load_percentage, run_no, group_name, "avg_throughput_megabit_per_s_average")] = np.mean(avg_throughput_megabit_per_s_list)
            statistics[(target_load_percentage, run_no, group_name, "avg_throughput_megabit_per_s_median")] = np.median(avg_throughput_megabit_per_s_list)
            statistics[(target_load_percentage, run_no, group_name, "avg_throughput_megabit_per_s_75th_percentile")] = np.percentile(avg_throughput_megabit_per_s_list, 75.0)
            statistics[(target_load_percentage, run_no, group_name, "avg_throughput_megabit_per_s_90th_percentile")] = np.percentile(avg_throughput_megabit_per_s_list, 90.0)
            statistics[(target_load_percentage, run_no, group_name, "avg_throughput_megabit_per_s_99th_percentile")] = np.percentile(avg_throughput_megabit_per_s_list, 99.0)
            statistics[(target_load_percentage, run_no, group_name, "avg_throughput_megabit_per_s_99_9th_percentile")] = np.percentile(avg_throughput_megabit_per_s_list, 99.9)
            statistics[(target_load_percentage, run_no, group_name, "avg_throughput_megabit_per_s_max")] = np.max(avg_throughput_megabit_per_s_list)

    # Retrieve target load percentage list and number of runs
    if len(list_target_load_percentage_with_run_no) != len(set(list_target_load_percentage_with_run_no)):
        raise ValueError("Duplicate arrival rate and run number combination")
    target_load_percentage_set = set()
    number_of_runs = -1
    for target_load_percentage, run_no in list_target_load_percentage_with_run_no:
        target_load_percentage_set.add(target_load_percentage)
        number_of_runs = max(number_of_runs, run_no + 1)
    target_load_percentage_list = list(sorted(list(target_load_percentage_set)))

    # All statistic group_names
    statistic_group_names = []
    for g in range(len(flow_groups_name_and_size)):
        statistic_group_names.append(flow_groups_name_and_size[g][0])
    statistic_group_names.append("all")

    # Write to a data file everything that might be interesting
    for static_group_name in statistic_group_names:
        for chosen_statistic_name in [
            "fraction_completed",
            "fct_ns_min",
            "fct_ns_0_1th_percentile",
            "fct_ns_1th_percentile",
            "fct_ns_10th_percentile",
            "fct_ns_25th_percentile",
            "fct_ns_average",
            "fct_ns_median",
            "fct_ns_75th_percentile",
            "fct_ns_90th_percentile",
            "fct_ns_99th_percentile",
            "fct_ns_99_9th_percentile",
            "fct_ns_max",
            "avg_throughput_megabit_per_s_min",
            "avg_throughput_megabit_per_s_0_1th_percentile",
            "avg_throughput_megabit_per_s_1th_percentile",
            "avg_throughput_megabit_per_s_10th_percentile",
            "avg_throughput_megabit_per_s_25th_percentile",
            "avg_throughput_megabit_per_s_average",
            "avg_throughput_megabit_per_s_median",
            "avg_throughput_megabit_per_s_75th_percentile",
            "avg_throughput_megabit_per_s_90th_percentile",
            "avg_throughput_megabit_per_s_99th_percentile",
            "avg_throughput_megabit_per_s_99_9th_percentile",
            "avg_throughput_megabit_per_s_max",
        ]:
            with open(data_dir + "/%s_%s.csv" % (static_group_name, chosen_statistic_name), "w+") as file_data:
                for target_load_percentage in target_load_percentage_list:
                    values = []
                    for run_no in range(number_of_runs):
                        values.append(
                            statistics[(target_load_percentage, run_no, static_group_name, chosen_statistic_name)]
                        )
                    # Completion time in nanoseconds has max of about 200s = 200e9,
                    # so precision should be around 3 decimals to accommodate for the current longest run
                    # Megabit/s has max of about 10000, so precision can be 6 decimals
                    # The lower bound of the two results in 3 decimal places
                    file_data.write("%.6f,%.3f,%.3f,%.3f,%d\n" % (
                        target_load_percentage,
                        np.mean(values),
                        np.min(values),
                        np.max(values),
                        len(values)
                    ))


def gen_basic_sim_utilization_plot_data(experiment_plot_dir, data_path, list_run_dir, spine_id_list):

    # Create the output directories if they don't exist yet
    data_dir = experiment_plot_dir + "/" + data_path
    os.makedirs(data_dir, exist_ok=True)

    # Collect the statistics
    list_target_load_percentage_with_run_no = []
    statistics = {}
    for run_dir in list_run_dir:

        # Currently working on
        logs_ns3_dir = run_dir + "/logs_ns3"
        print("Handling run: " + run_dir)

        # We evaluate the different runs for each flow arrival rate
        with open(run_dir + "/data-structure.txt", "r") as f_in:
            run_data_structure = ast.literal_eval(f_in.read())
            target_load_percentage = run_data_structure["load_with_lambda_flow_arrival_rate"][1][0]
            expected_flows_per_s = run_data_structure["load_with_lambda_flow_arrival_rate"][1][1]
            run_no = run_data_structure["run_number"][1]
            list_target_load_percentage_with_run_no.append((target_load_percentage, run_no))
            total_expected_num_flows = run_data_structure["total_expected_num_flows"][1]
            duration_ns = int(math.ceil(float(total_expected_num_flows) / float(expected_flows_per_s) * 1000000000))
            warm_up_ns = run_data_structure["warm_up_ns"][1]
            cool_down_ns = run_data_structure["cool_down_ns"][1]
            duration_ns += warm_up_ns + cool_down_ns

            # Read in utilization file
            utilization_csv_columns = exputil.read_csv_direct_in_columns(
                logs_ns3_dir + "/link_net_device_utilization.csv",
                "pos_int,pos_int,pos_int,pos_int,pos_int"
            )
            total_num_utilization_entries = len(utilization_csv_columns[0])
            from_node_id_list = utilization_csv_columns[0]
            to_node_id_list = utilization_csv_columns[1]
            interval_start_incl_ns_list = utilization_csv_columns[2]
            interval_end_incl_ns_list = utilization_csv_columns[3]
            busy_time_ns_list = utilization_csv_columns[4]

            link_pair_to_utilization = {}
            for i in range(total_num_utilization_entries):
                if interval_start_incl_ns_list[i] >= warm_up_ns and interval_end_incl_ns_list[i] <= duration_ns - cool_down_ns:
                    link_pair = (from_node_id_list[i], to_node_id_list[i])
                    if link_pair not in link_pair_to_utilization:
                        link_pair_to_utilization[link_pair] = (0, 0)
                    link_pair_to_utilization[link_pair] = (
                        link_pair_to_utilization[link_pair][0] + interval_end_incl_ns_list[i] - interval_start_incl_ns_list[i],
                        link_pair_to_utilization[link_pair][1] + busy_time_ns_list[i]
                    )

            # The two groups
            links_server_leaf_average_utilization = []
            links_leaf_spine_average_utilization = []
            for link_pair in link_pair_to_utilization:
                if link_pair[0] in spine_id_list or link_pair[1] in spine_id_list:
                    links_leaf_spine_average_utilization.append(
                        link_pair_to_utilization[link_pair][1] / link_pair_to_utilization[link_pair][0]
                    )
                else:
                    links_server_leaf_average_utilization.append(
                        link_pair_to_utilization[link_pair][1] / link_pair_to_utilization[link_pair][0]
                    )
                    
            for groups in [
                ("server_leaf", links_server_leaf_average_utilization),
                ("leaf_spine", links_leaf_spine_average_utilization),
            ]:
                group_name = groups[0]
                link_average_utilization = groups[1]

                # FCT statistics
                statistics[(target_load_percentage, run_no, group_name, "link_utilization_fraction_min")] = np.min(link_average_utilization)
                statistics[(target_load_percentage, run_no, group_name, "link_utilization_fraction_1th_percentile")] = np.percentile(link_average_utilization, 1.0)
                statistics[(target_load_percentage, run_no, group_name, "link_utilization_fraction_10th_percentile")] = np.percentile(link_average_utilization, 10.0)
                statistics[(target_load_percentage, run_no, group_name, "link_utilization_fraction_25th_percentile")] = np.percentile(link_average_utilization, 25.0)
                statistics[(target_load_percentage, run_no, group_name, "link_utilization_fraction_average")] = np.mean(link_average_utilization)
                statistics[(target_load_percentage, run_no, group_name, "link_utilization_fraction_median")] = np.median(link_average_utilization)
                statistics[(target_load_percentage, run_no, group_name, "link_utilization_fraction_75th_percentile")] = np.percentile(link_average_utilization, 75.0)
                statistics[(target_load_percentage, run_no, group_name, "link_utilization_fraction_90th_percentile")] = np.percentile(link_average_utilization, 90.0)
                statistics[(target_load_percentage, run_no, group_name, "link_utilization_fraction_99th_percentile")] = np.percentile(link_average_utilization, 99.0)
                statistics[(target_load_percentage, run_no, group_name, "link_utilization_fraction_max")] = np.max(link_average_utilization)

    # Retrieve target load percentage list and number of runs
    if len(list_target_load_percentage_with_run_no) != len(set(list_target_load_percentage_with_run_no)):
        raise ValueError("Duplicate arrival rate and run number combination")
    target_load_percentage_set = set()
    number_of_runs = -1
    for target_load_percentage, run_no in list_target_load_percentage_with_run_no:
        target_load_percentage_set.add(target_load_percentage)
        number_of_runs = max(number_of_runs, run_no + 1)
    target_load_percentage_list = list(sorted(list(target_load_percentage_set)))

    for chosen_statistic_name in [
        "link_utilization_fraction_min",
        "link_utilization_fraction_1th_percentile",
        "link_utilization_fraction_10th_percentile",
        "link_utilization_fraction_25th_percentile",
        "link_utilization_fraction_average",
        "link_utilization_fraction_median",
        "link_utilization_fraction_75th_percentile",
        "link_utilization_fraction_90th_percentile",
        "link_utilization_fraction_99th_percentile",
        "link_utilization_fraction_max",
    ]:
        for group_name in ["server_leaf", "leaf_spine"]:
            with open(data_dir + "/%s_%s.csv" % (group_name, chosen_statistic_name), "w+") as file_data:
                for target_load_percentage in target_load_percentage_list:
                    values = []
                    for run_no in range(number_of_runs):
                        values.append(
                            statistics[(target_load_percentage, run_no, group_name, chosen_statistic_name)]
                        )
                    # Link utilization fraction is in the range of [0, 1], as such 6 decimal precision works
                    file_data.write("%.6f,%.6f,%.6f,%.6f,%d\n" % (
                        target_load_percentage,
                        np.mean(values),
                        np.min(values),
                        np.max(values),
                        len(values)
                    ))
