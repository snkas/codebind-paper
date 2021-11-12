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

import re
import exputil
import os
from hashlib import sha256
import math
import random
import copy
import ast


# Import the abstract class for interpreter
from .rootclassinterpreter import (
    RootClassInterpreter,
    InterpretExplineError,
    RunDirGenerationError
)

# Import the abstract class for plotter
from .rootclassplotter import (
    RootClassPlotter,
    InvalidRunDirError,
    PlotExpincludeError
)

# Utility functions
from .rootclassutility import (
    flatten_brace_group_to_str,
    expand_regex_to_be_tolerant_to_whitespace
)

# Import some common network argument parsing utilities
from .helper.utilityunitparser import (
    parse_congestion_protocol,
    parse_texish_data_to_byte,
    parse_texish_time_to_ns,
    parse_texish_percentage,
    parse_texish_int_percentage
)

from .helper.bsincorporators import (
    incorporator_link_channel_and_network_devices,
    incorporate_tcp_settings_using_identifier,
    incorporator_delayed_ack,
    incorporator_buffer_size
)

from .helper.bsgenplotdata import (
    gen_basic_sim_tcp_flows_plot_data,
    gen_basic_sim_utilization_plot_data
)


def draw_n_times_from_to_all_to_all(n, servers, seed):

    # No duplicates in the servers array
    if len(set(servers)) != len(servers):
        raise ValueError("There are duplicate entries in the servers array: " + str(servers))
    if len(servers) < 2:
        raise ValueError("Cannot have less than two servers")
    servers = list(servers)

    # Set random seed
    random.seed(seed)

    # Draw n times
    from_to_tuples = []
    for i in range(n):
        src = random.randint(0, len(servers) - 1)
        dst = random.randint(0, len(servers) - 1)
        while src == dst:
            dst = random.randint(0, len(servers) - 1)
        from_to_tuples.append((servers[src], servers[dst]))

    return from_to_tuples


def draw_poisson_inter_arrival_gap(lambda_mean_arrival_rate):
    """
    Draw a poisson inter-arrival gap.
    It uses random as random source, so be sure to set random.seed(...) beforehand for reproducibility.

    E.g.:
    If lambda = 1000, then mean gap is 0.001
    If lambda = 0.1, then mean gap is 10

    :param lambda_mean_arrival_rate:     Lambda mean arrival rate (i.e., every 1 in ... an event arrives)

    :return: Value drawn from the exponential distribution (i.e., Poisson inter-arrival distribution)
    """
    return - math.log(1.0 - random.random(), math.e) / lambda_mean_arrival_rate


def draw_poisson_inter_arrival_gap_start_times_ns(duration_ns, lambda_mean_arrival_rate_flows_per_s, seed):
    random.seed(seed)
    start_times_ns = []
    s = 1e9 * draw_poisson_inter_arrival_gap(lambda_mean_arrival_rate_flows_per_s)
    while int(round(s)) < duration_ns:
        start_times_ns.append(int(round(s)))
        s += 1e9 * draw_poisson_inter_arrival_gap(lambda_mean_arrival_rate_flows_per_s)
    return start_times_ns


def get_mean_statistic(
        exp_instance_name,
        filename_plot,
        target_load,
        data_filename,
):
    data = exputil.read_csv_direct_in_columns(
        data_filename,
        "pos_float,pos_float,pos_float,pos_float,pos_int"
    )
    list_target_load = data[0]
    list_mean = data[1]
    # list_min = data[2]
    # list_max = data[3]
    # list_count = data[4]
    mean_statistic_value = -1
    for i in range(len(list_target_load)):
        if list_target_load[i] == target_load:
            mean_statistic_value = list_mean[i]
    if mean_statistic_value == -1:
        raise PlotExpincludeError(
            exp_instance_name, filename_plot,
            "Target load does not exist among the plot data files: " + str(target_load)
        )
    return mean_statistic_value


def retrieve_flow_arrival_rate_of_target_load(
        exp_instance_name,
        filename_plot,
        list_load_with_lambda_flow_arrival_rates,
        target_load
):
    matching_flow_arrival_rate = -1
    for item_load, item_flow_arrival_rate in list_load_with_lambda_flow_arrival_rates:
        if item_load == target_load:
            matching_flow_arrival_rate = item_flow_arrival_rate
            break
    if matching_flow_arrival_rate == -1:
        raise PlotExpincludeError(
            exp_instance_name, filename_plot,
            "Target load does not exist amongst the experiment data structures: " + str(target_load)
        )
    return matching_flow_arrival_rate


def calculate_mean_flow_size_byte_from_data_structure(data_structure):
    small_flow_size_byte = data_structure["small_flow_size_byte"][1]
    large_flow_size_byte = data_structure["large_flow_size_byte"][1]
    small_flow_probability = data_structure["small_flow_probability"][1]
    return (
            float(small_flow_probability) * float(small_flow_size_byte) +
            float(1.0 - small_flow_probability) * float(large_flow_size_byte)
    )


def calculate_all_to_all_max_load_from_data_structure(data_structure):
    num_spines = data_structure["num_spines"][1]
    num_leafs = data_structure["num_leafs"][1]
    num_server_per_leaf = data_structure["num_servers_per_leaf"][1]
    data_rate_megabit_per_s = data_structure["link_net_device_data_rate_megabit_per_s"][1]
    total_num_servers = num_leafs * num_server_per_leaf
    fraction_server_sends_to_other_leafs = (total_num_servers - num_server_per_leaf) / (total_num_servers - 1)
    leaf_to_spines_bottleneck_hit_at = num_spines / (fraction_server_sends_to_other_leafs * num_server_per_leaf)
    max_load_in_sum_of_server_sending_rate_fraction = min(
        1.0,
        leaf_to_spines_bottleneck_hit_at
    )
    max_load_megabit_per_s = (
            max_load_in_sum_of_server_sending_rate_fraction * total_num_servers * data_rate_megabit_per_s
    )
    return max_load_megabit_per_s


class LoadLeafSpineRootClassInterpreter(RootClassInterpreter):

    def __init__(self):
        self.root_class_name = "load-ls"

    def get_root_class_name(self):
        return self.root_class_name

    def generate_empty_experiment_data_structure(self):
        return {
            "total_expected_num_flows": (False, None),  # Integer > 0
            "link_channel_delay_ns": (False, None),  # Integer >= 0
            "link_net_device_data_rate_megabit_per_s": (False, None),  # Float > 0
            "link_net_device_queue": (False, None),  # String (e.g., "drop_tail(100p)")
            "link_net_device_receive_error_model": (False, None),  # String (e.g., "none",
                                                                   # "iid_uniform_random_pkt(0.001)")
            "link_interface_traffic_control_qdisc": (False, None),  # String (e.g., "disabled", "fifo(100p)")
            "num_leafs": (False, None),  # Integer > 0
            "num_spines": (False, None),  # Integer > 0
            "num_servers_per_leaf": (False, None),  # Integer > 0
            "load_with_lambda_flow_arrival_rate": (False, None),  # Tuple (load (integer), lambda (double))
                                                                  # or list thereof
            "small_flow_priority": (True, ["low", "high"]),  # String, "low" or "high"
            "small_flow_size_byte": (False, None),  # Integer > 0
            "large_flow_size_byte": (False, None),  # Integer > 0
            "small_flow_probability": (False, None),  # Float >= 0 <= 1
            "warm_up_ns": (False, None),  # Integer > 0
            "cool_down_ns": (False, None),  # Integer > 0
            "run_number": (False, None),  # Integer or list of integers

            # TCP settings
            "tcp_protocol": (False, None),  # String ("NewReno", "Cubic", "Vegas", "DCTCP")
            "tcp_snd_buf_size_byte": (False, None),  # Integer
            "tcp_rcv_buf_size_byte": (False, None),  # Integer
            "tcp_init_cwnd_pkt": (False, None),  # Integer
            "tcp_segment_size_byte": (False, None),  # Integer
            "tcp_opt_timestamp_enabled": (False, None),  # String boolean ("true" or "false")
            "tcp_opt_sack_enabled": (False, None),  # String boolean ("true" or "false")
            "tcp_opt_win_scaling_enabled": (False, None),  # String boolean ("true" or "false")
            "tcp_opt_pacing_enabled": (False, None),  # String boolean ("true" or "false")
            "tcp_delayed_ack_packet_count": (False, None),  # Integer
            "tcp_no_delay": (False, None),  # String boolean ("true" or "false")
            "tcp_max_seg_lifetime_ns": (False, None),  # Integer
            "tcp_min_rto_ns": (False, None),  # Integer
            "tcp_initial_rtt_estimate_ns": (False, None),  # Integer
            "tcp_connection_timeout_ns": (False, None),  # Integer
            "tcp_delayed_ack_timeout_ns": (False, None),  # Integer
            "tcp_persist_timeout_ns": (False, None),  # Integer
        }

    def interpret_expline_into_experiment_data_structure(self, exp_name, expline_identifier, expline, data_structure):

        # TCP settings
        if incorporate_tcp_settings_using_identifier(exp_name, expline_identifier, expline, data_structure):
            return data_structure

        # Buffer size
        # Example:
        # The send and receive buffer size are set to 1~GB
        if incorporator_buffer_size(exp_name, expline_identifier, expline, data_structure):
            return data_structure

        # Delayed ACK
        # Example:
        # Delayed acknowledgements are disabled
        if incorporator_delayed_ack(exp_name, expline_identifier, expline, data_structure):
            return data_structure

        # Link channel and network devices
        # Example:
        # Every/The link has the following properties: the channel has a delay of 10~$\mu s$, and its link network
        # devices have a data rate of 50~Mbit/s, 0.1\% random packet loss, and a FIFO queue of 100 packets.
        if incorporator_link_channel_and_network_devices(exp_name, expline_identifier, expline, data_structure):
            return data_structure

        # Example:
        # The experiment is configured such that in expectation 10000 flows start in the measurement period.
        result = re.match(
            expand_regex_to_be_tolerant_to_whitespace(
                r'[Tt]he experiment is configured such that in expectation (.*) '
                r'flows start in the measurement period\.?'
            ),
            flatten_brace_group_to_str(expline)
        )
        if result is not None:
            subgroups = result.groups()
            total_flows = exputil.parse_positive_int(subgroups[0])
            if data_structure["total_expected_num_flows"][0]:
                raise InterpretExplineError(exp_name, expline_identifier, expline, "Total flows is already set")
            data_structure["total_expected_num_flows"] = (True, total_flows)
            return data_structure

        # Example:
        # We set pfifo\_fast as the queueing discipline with a maximum total queue size of 100 packets.
        result = re.match(
            expand_regex_to_be_tolerant_to_whitespace(
                r'We set pfifo\\_fast as the queueing discipline with a maximum total queue size of (.*) packets\.?'
            ),
            flatten_brace_group_to_str(expline)
        )
        if result is not None:
            subgroups = result.groups()
            max_queue_size_pkt = exputil.parse_positive_int(subgroups[0])
            if data_structure["link_interface_traffic_control_qdisc"][0]:
                raise InterpretExplineError(exp_name, expline_identifier, expline, "Qdisc is already set")
            data_structure["link_interface_traffic_control_qdisc"] = (
                True,
                "pfifo_fast(%dp)" % max_queue_size_pkt
            )
            return data_structure

        # Example:
        # We set DCTCP as the congestion control protocol.
        result = re.match(
            expand_regex_to_be_tolerant_to_whitespace(
                r'[Ww]e set (.*) as the congestion control protocol\.?'
            ),
            flatten_brace_group_to_str(expline)
        )
        if result is not None:
            subgroups = result.groups()
            if data_structure["tcp_protocol"][0]:
                raise InterpretExplineError(exp_name, expline_identifier, expline, "Protocol is already set")
            data_structure["tcp_protocol"] = (
                True,
                parse_congestion_protocol(exp_name, expline_identifier, expline, subgroups[0])
            )
            return data_structure

        # Example:
        # There are 3 spines and 4 leaves.
        result = re.match(
            expand_regex_to_be_tolerant_to_whitespace(
                r'[Tt]here are (.*) spines and (.*) leaves\.?'
            ),
            flatten_brace_group_to_str(expline)
        )
        if result is not None:
            subgroups = result.groups()

            num_spines = exputil.parse_positive_int(subgroups[0])
            if num_spines < 1:
                raise InterpretExplineError(
                    exp_name, expline_identifier, expline, "Number of spines must be at least 1"
                )
            if data_structure["num_spines"][0]:
                raise InterpretExplineError(
                    exp_name, expline_identifier, expline, "Number of spines is already set"
                )
            data_structure["num_spines"] = (True, num_spines)

            num_leafs = exputil.parse_positive_int(subgroups[1])
            if num_leafs < 1:
                raise InterpretExplineError(exp_name, expline_identifier, expline, "Number of leafs must be at least 1")
            if data_structure["num_leafs"][0]:
                raise InterpretExplineError(exp_name, expline_identifier, expline, "Number of leafs is already set")
            data_structure["num_leafs"] = (True, num_leafs)
            return data_structure

        # Example:
        # Each leaf (ToR) has 5 servers underneath.
        result = re.match(
            expand_regex_to_be_tolerant_to_whitespace(
                r'[Ee]ach leaf \(ToR\) has (.*) servers underneath\.?'
            ),
            flatten_brace_group_to_str(expline)
        )
        if result is not None:
            subgroups = result.groups()

            num_servers_per_leaf = exputil.parse_positive_int(subgroups[0])
            if num_servers_per_leaf < 1:
                raise InterpretExplineError(
                    exp_name, expline_identifier, expline, "Number of servers per leaf (ToR) must be at least 1"
                )
            if data_structure["num_servers_per_leaf"][0]:
                raise InterpretExplineError(
                    exp_name, expline_identifier, expline, "Number of servers per leaf (ToR) is already set"
                )
            data_structure["num_servers_per_leaf"] = (True, num_servers_per_leaf)
            return data_structure
        
        # Example:
        # Each load point is run for 5 times, with a reproducible initial random seed based on the
        # (SHA-256) hash of the run data structure (which includes run number).
        result = re.match(
            expand_regex_to_be_tolerant_to_whitespace(
                r'[Ee]ach load point is run for (.*) times, with a reproducible initial random seed based on the'
                r' \(SHA-256\) hash of its unique run configuration\.?'
            ),
            flatten_brace_group_to_str(expline)
        )
        if result is not None:
            subgroups = result.groups()

            num_runs = exputil.parse_positive_int(subgroups[0])
            if num_runs < 1:
                raise InterpretExplineError(
                    exp_name, expline_identifier, expline, "Number of runs must be at least 1"
                )
            if data_structure["run_number"][0]:
                raise InterpretExplineError(
                    exp_name, expline_identifier, expline, "Number of runs is already set"
                )
            data_structure["run_number"] = (True, list(range(0, num_runs)))

            return data_structure

        # Example:
        # The heaviness of the load is determined by $\lambda$,
        # which we increase from 100 till 1000 flow/s in steps of 100."
        result = re.match(
            expand_regex_to_be_tolerant_to_whitespace(
                r'[Ww]e vary the target load from (.*) till (.*) in increments of ([^\.]*)\.?'
            ),
            flatten_brace_group_to_str(expline)
        )
        if result is not None:
            subgroups = result.groups()

            if (
                    not data_structure["num_spines"][0]
                    or not data_structure["num_leafs"][0]
                    or not data_structure["num_servers_per_leaf"][0]
                    or not data_structure["link_net_device_data_rate_megabit_per_s"][0]
                    or not data_structure["small_flow_size_byte"][0]
                    or not data_structure["large_flow_size_byte"][0]
                    or not data_structure["small_flow_probability"][0]
            ):
                raise InterpretExplineError(
                    exp_name,
                    expline_identifier,
                    expline,
                    "Can only set load when Bernoulli flow size distribution, spines, leafs, "
                    "servers/leaf and link net-device data rate are set"
                )
            expected_mean_flow_size_byte = calculate_mean_flow_size_byte_from_data_structure(data_structure)
            max_load_megabit_per_s = calculate_all_to_all_max_load_from_data_structure(data_structure)
            max_load_flows_per_s = max_load_megabit_per_s / (expected_mean_flow_size_byte / 125000.0)

            load_from = parse_texish_int_percentage(exp_name, expline_identifier, expline, subgroups[0])
            load_to = parse_texish_int_percentage(exp_name, expline_identifier, expline, subgroups[1])
            load_step = parse_texish_int_percentage(exp_name, expline_identifier, expline, subgroups[2])

            if (
                load_from < 1 or
                load_to < 1 or
                load_step < 1 or
                load_from > load_to or
                (load_to - load_from) % load_step != 0 or
                (load_to - load_from) / load_step < 1
            ):
                raise InterpretExplineError(
                    exp_name,
                    expline_identifier,
                    expline,
                    "Invalid load: from %d to %d in steps of %d" % (
                        load_from, load_to, load_step
                    )
                )
            if data_structure["load_with_lambda_flow_arrival_rate"][0]:
                raise InterpretExplineError(
                    exp_name, expline_identifier, expline, "Load with lambda flow arrival rate is already set"
                )

            if load_step / 100.0 * max_load_flows_per_s <= 0.01:
                raise InterpretExplineError(
                    exp_name, expline_identifier, expline, "Proposed step is too small."
                )
            lambda_step_per_load_percentage = round(1.0 / 100.0 * max_load_flows_per_s, 4)
            list_load_with_lambda_flow_arrival_rate = []
            for load in range(load_from, load_to + load_step, load_step):
                list_load_with_lambda_flow_arrival_rate.append((
                    load,
                    round(load * lambda_step_per_load_percentage, 4)
                ))
            data_structure["load_with_lambda_flow_arrival_rate"] = (
                True,
                list_load_with_lambda_flow_arrival_rate
            )

            return data_structure

        # Example:
        # The flow size is randomly chosen to be either small (50 KB) with 90% probability,
        # or large (4 MB) with 10% probability.
        result = re.match(
            expand_regex_to_be_tolerant_to_whitespace(
                r'[Tt]he flow size is randomly chosen to be either small \((.*)\) '
                r'with (.*) probability, or large \((.*)\) with (.*) probability\.?'
            ),
            flatten_brace_group_to_str(expline)
        )
        if result is not None:
            subgroups = result.groups()
            small_flow_size_byte = parse_texish_data_to_byte(exp_name, expline_identifier, expline, subgroups[0])
            small_flow_probability = parse_texish_percentage(exp_name, expline_identifier, expline, subgroups[1])
            large_flow_size_byte = parse_texish_data_to_byte(exp_name, expline_identifier, expline, subgroups[2])
            large_flow_probability = parse_texish_percentage(exp_name, expline_identifier, expline, subgroups[3])

            if small_flow_probability + large_flow_probability != 100.0:
                raise InterpretExplineError(
                    exp_name, expline_identifier, expline, "Small and large flow probability do not add up"
                )

            if data_structure["small_flow_size_byte"][0]:
                raise InterpretExplineError(
                    exp_name, expline_identifier, expline, "Small flow size is already set"
                )
            data_structure["small_flow_size_byte"] = (True, small_flow_size_byte)

            if data_structure["large_flow_size_byte"][0]:
                raise InterpretExplineError(
                    exp_name, expline_identifier, expline, "Large flow size is already set"
                )
            data_structure["large_flow_size_byte"] = (True, large_flow_size_byte)

            if data_structure["small_flow_probability"][0]:
                raise InterpretExplineError(
                    exp_name, expline_identifier, expline, "Small flow probability is already set"
                )
            data_structure["small_flow_probability"] = (True, small_flow_probability / 100.0)

            return data_structure

        # Example:
        # Only the flows which did start not in the warm-up period of the first
        # 2~seconds and the cool-down period of the last 4~seconds are used for the results.
        result = re.match(
            expand_regex_to_be_tolerant_to_whitespace(
                r'[Oo]nly the flows which start in the measurement period are included in the result: '
                r'the flows which started in the warm-up period of the '
                r'first (.*) and the cool-down period of the last (.*) are not taken into account\.?'
            ),
            flatten_brace_group_to_str(expline)
        )
        if result is not None:
            subgroups = result.groups()

            warm_up_ns = parse_texish_time_to_ns(exp_name, expline_identifier, expline, subgroups[0])
            if data_structure["warm_up_ns"][0]:
                raise InterpretExplineError(exp_name, expline_identifier, expline, "Warm-up is already set")
            data_structure["warm_up_ns"] = (True, warm_up_ns)

            cool_down_ns = parse_texish_time_to_ns(exp_name, expline_identifier, expline, subgroups[1])
            if data_structure["cool_down_ns"][0]:
                raise InterpretExplineError(exp_name, expline_identifier, expline, "Cool-down is already set")
            data_structure["cool_down_ns"] = (True, cool_down_ns)

            return data_structure

        # If nothing matched, then it failed
        raise InterpretExplineError(exp_name, expline_identifier, expline, "Did not match any pattern.")

    def generate_run_dirs_for_experiment_data_structure(self, exp_instance_name, runs_path, data_structure):

        # Check validity of data structure
        if not data_structure["total_expected_num_flows"][0]:
            raise RunDirGenerationError(exp_instance_name, "Total number of flows is not set")
        if not data_structure["link_channel_delay_ns"][0]:
            raise RunDirGenerationError(exp_instance_name, "Channel delay is not set")
        if not data_structure["link_net_device_data_rate_megabit_per_s"][0]:
            raise RunDirGenerationError(exp_instance_name, "Device data rate is not set")
        if not data_structure["link_net_device_queue"][0]:
            raise RunDirGenerationError(exp_instance_name, "Device queue is not set")
        if not data_structure["link_net_device_receive_error_model"][0]:
            raise RunDirGenerationError(exp_instance_name, "Device error model is not set")
        if not data_structure["link_interface_traffic_control_qdisc"][0]:
            raise RunDirGenerationError(exp_instance_name, "Interface traffic-control qdisc is not set")
        if not data_structure["num_leafs"][0]:
            raise RunDirGenerationError(exp_instance_name, "Number of leafs is not set")
        if not data_structure["num_spines"][0]:
            raise RunDirGenerationError(exp_instance_name, "Number of spines is not set")
        if not data_structure["num_servers_per_leaf"][0]:
            raise RunDirGenerationError(exp_instance_name, "Number of servers / leaf is not set")
        if not data_structure["load_with_lambda_flow_arrival_rate"][0]:
            raise RunDirGenerationError(exp_instance_name, "Load with lambda arrival rate is not set")
        if not data_structure["small_flow_size_byte"][0]:
            raise RunDirGenerationError(exp_instance_name, "Small flow size is not set")
        if not data_structure["large_flow_size_byte"][0]:
            raise RunDirGenerationError(exp_instance_name, "Large flow size is not set")
        if not data_structure["small_flow_probability"][0]:
            raise RunDirGenerationError(exp_instance_name, "Small flow probability is not set")
        if not data_structure["warm_up_ns"][0]:
            raise RunDirGenerationError(exp_instance_name, "Warm-up is not set")
        if not data_structure["cool_down_ns"][0]:
            raise RunDirGenerationError(exp_instance_name, "Cool-down is not set")
        if not data_structure["run_number"][0]:
            raise RunDirGenerationError(exp_instance_name, "Run number is not set")
        if not data_structure["small_flow_priority"][0]:
            raise RunDirGenerationError(exp_instance_name, "Small flow priority is not set")
        if not data_structure["tcp_protocol"][0]:
            raise RunDirGenerationError(exp_instance_name, "Protocol is not set")
        if not data_structure["tcp_snd_buf_size_byte"][0]:
            raise RunDirGenerationError(exp_instance_name, "Send buffer size is not set")
        if not data_structure["tcp_rcv_buf_size_byte"][0]:
            raise RunDirGenerationError(exp_instance_name, "Receive buffer size is not set")
        if not data_structure["tcp_init_cwnd_pkt"][0]:
            raise RunDirGenerationError(exp_instance_name, "Initial congestion window is not set")
        if not data_structure["tcp_segment_size_byte"][0]:
            raise RunDirGenerationError(exp_instance_name, "Segment size is not set")
        if not data_structure["tcp_opt_timestamp_enabled"][0]:
            raise RunDirGenerationError(exp_instance_name, "Timestamp option enabled is not set")
        if not data_structure["tcp_opt_sack_enabled"][0]:
            raise RunDirGenerationError(exp_instance_name, "SACK option enabled is not set")
        if not data_structure["tcp_opt_win_scaling_enabled"][0]:
            raise RunDirGenerationError(exp_instance_name, "Window scaling option enabled is not set")
        if not data_structure["tcp_opt_pacing_enabled"][0]:
            raise RunDirGenerationError(exp_instance_name, "Pacing option enabled is not set")
        if not data_structure["tcp_delayed_ack_packet_count"][0]:
            raise RunDirGenerationError(exp_instance_name, "Delayed ACK packet count is not set")
        if not data_structure["tcp_no_delay"][0]:
            raise RunDirGenerationError(exp_instance_name, "No-delay enabling is not set")
        if not data_structure["tcp_max_seg_lifetime_ns"][0]:
            raise RunDirGenerationError(exp_instance_name, "Maximum segment lifetime is not set")
        if not data_structure["tcp_min_rto_ns"][0]:
            raise RunDirGenerationError(exp_instance_name, "Minimum RTO is not set")
        if not data_structure["tcp_initial_rtt_estimate_ns"][0]:
            raise RunDirGenerationError(exp_instance_name, "Initial RTT estimate is not set")
        if not data_structure["tcp_connection_timeout_ns"][0]:
            raise RunDirGenerationError(exp_instance_name, "Connection timeout is not set")
        if not data_structure["tcp_delayed_ack_timeout_ns"][0]:
            raise RunDirGenerationError(exp_instance_name, "Delayed ACK timeout is not set")
        if not data_structure["tcp_persist_timeout_ns"][0]:
            raise RunDirGenerationError(exp_instance_name, "Persist timeout is not set")

        # Flow arrival rates
        list_load_with_lambda_flow_arrival_rate = []
        if isinstance(data_structure["load_with_lambda_flow_arrival_rate"][1], list):
            list_load_with_lambda_flow_arrival_rate.extend(data_structure["load_with_lambda_flow_arrival_rate"][1])
        else:
            list_load_with_lambda_flow_arrival_rate.append(data_structure["load_with_lambda_flow_arrival_rate"][1])

        # Number of runs
        run_numbers = []
        if isinstance(data_structure["run_number"][1], list):
            run_numbers.extend(data_structure["run_number"][1])
        else:
            run_numbers.append(data_structure["run_number"][1])

        # IP TOS
        small_flow_priorities = []
        if isinstance(data_structure["small_flow_priority"][1], list):
            small_flow_priorities.extend(data_structure["small_flow_priority"][1])
        else:
            small_flow_priorities.append(data_structure["small_flow_priority"][1])

        # Generate all single-valued run data structures
        all_run_data_structures = []
        for load_with_lambda_flow_arrival_rate in list_load_with_lambda_flow_arrival_rate:
            for run_number in run_numbers:
                for small_flow_priority in small_flow_priorities:
                    new_data_structure = copy.deepcopy(data_structure)
                    new_data_structure["load_with_lambda_flow_arrival_rate"] = True, load_with_lambda_flow_arrival_rate
                    new_data_structure["run_number"] = True, run_number
                    new_data_structure["small_flow_priority"] = True, small_flow_priority
                    all_run_data_structures.append(new_data_structure)

        # Finally, create a run directory for each data structure
        list_run_dir_names = []
        for run_data_structure in all_run_data_structures:

            # Calculate the hash of the data structure
            run_sha256 = sha256(repr(sorted(run_data_structure.items())).encode('utf-8'))
            run_hash = run_sha256.hexdigest()
            run_master_seed = int.from_bytes(run_sha256.digest(), 'big')

            # Create the run directory
            run_dir_name = self.root_class_name + "-" + str(run_hash)
            list_run_dir_names.append(run_dir_name)
            run_dir_path = runs_path + "/" + run_dir_name
            os.makedirs(run_dir_path, exist_ok=True)

            # Open the data-structure.txt file if it exists, and compare to make sure we don't
            # have a weird duplicate SHA-256 hash (unlikely, but could happen if the hashing
            # of the run data structure was done incorrectly)
            if os.path.exists(run_dir_path + "/data-structure.txt"):
                with open(run_dir_path + "/data-structure.txt", "r") as f_in:
                    content = f_in.read()
                    if content != str(run_data_structure):
                        raise ValueError("Hash matched, but data structure was not equal!")

            # Check if already everything exists
            not_ready = True
            if os.path.exists(run_dir_path + "/input-ready.txt"):
                with open(run_dir_path + "/input-ready.txt", "w+") as f_ready_to_run:
                    if f_ready_to_run.read().strip() == "Yes":
                        not_ready = False

            # Only if not yet ready, write the data files again
            if not_ready:

                # Write the data structure to the data-structure.txt file
                with open(run_dir_path + "/data-structure.txt", "w+") as f_out:
                    f_out.write(str(run_data_structure))

                # We write some info for the master seed just to check
                with open(run_dir_path + "/master-seed.txt", "w+") as f_out:
                    f_out.write("SHA-256 digest: " + str(run_hash) + "\n")
                    f_out.write("Master seed (SHA-256 digest as integer): " + str(run_master_seed) + "\n")

                # Calculate duration

                # The duration is at least the measurement period
                total_expected_num_flows = run_data_structure["total_expected_num_flows"][1]
                # load = run_data_structure["load_with_lambda_flow_arrival_rate"][1][0]
                # Load is already encoded in the arrival rate value below
                lambda_arrival_rate = run_data_structure["load_with_lambda_flow_arrival_rate"][1][1]
                duration_ns = int(math.ceil(float(total_expected_num_flows) / float(lambda_arrival_rate) * 1000000000))

                # Plus fixed the warm-up and cool-down period
                warm_up_ns = run_data_structure["warm_up_ns"][1]
                cool_down_ns = run_data_structure["cool_down_ns"][1]
                duration_ns += warm_up_ns + cool_down_ns

                # Run configuration
                with open(run_dir_path + "/config_ns3.properties", "w+") as f_config:
                    f_config.write("simulation_end_time_ns=%d\n" % duration_ns)
                    f_config.write("simulation_seed=123456789\n")
                    f_config.write("topology_ptop_filename=\"ptop_topology.properties\"\n")
                    f_config.write("enable_link_net_device_utilization_tracking=true\n")
                    f_config.write("link_net_device_utilization_tracking_interval_ns=1000000000\n")
                    f_config.write("link_net_device_utilization_tracking_enable_for_links=all\n")
                    f_config.write("enable_tcp_flow_scheduler=true\n")
                    f_config.write("tcp_flow_schedule_filename=\"tcp_flow_schedule.csv\"\n")
                    f_config.write("tcp_flow_enable_logging_for_tcp_flow_ids=set()\n")
                    f_config.write("tcp_protocol=%s\n" % run_data_structure["tcp_protocol"][1])
                    f_config.write("tcp_config=custom\n")
                    f_config.write("tcp_clock_granularity_ns=1000000\n")  # 1ms clock granularity
                    f_config.write("tcp_snd_buf_size_byte=%d\n" % data_structure["tcp_snd_buf_size_byte"][1])
                    f_config.write("tcp_rcv_buf_size_byte=%d\n" % data_structure["tcp_rcv_buf_size_byte"][1])
                    f_config.write("tcp_init_cwnd_pkt=%d\n" % data_structure["tcp_init_cwnd_pkt"][1])
                    f_config.write("tcp_segment_size_byte=%d\n" % data_structure["tcp_segment_size_byte"][1])
                    f_config.write("tcp_opt_timestamp_enabled=%s\n" % data_structure["tcp_opt_timestamp_enabled"][1])
                    f_config.write("tcp_opt_sack_enabled=%s\n" % data_structure["tcp_opt_sack_enabled"][1])
                    f_config.write("tcp_opt_win_scaling_enabled=%s\n" % (
                        data_structure["tcp_opt_win_scaling_enabled"][1]
                    ))
                    f_config.write("tcp_opt_pacing_enabled=%s\n" % data_structure["tcp_opt_pacing_enabled"][1])
                    f_config.write("tcp_delayed_ack_packet_count=%d\n" % (
                        data_structure["tcp_delayed_ack_packet_count"][1]
                    ))
                    f_config.write("tcp_no_delay=%s\n" % data_structure["tcp_no_delay"][1])
                    f_config.write("tcp_max_seg_lifetime_ns=%d\n" % data_structure["tcp_max_seg_lifetime_ns"][1])
                    f_config.write("tcp_min_rto_ns=%d\n" % data_structure["tcp_min_rto_ns"][1])
                    f_config.write("tcp_initial_rtt_estimate_ns=%d\n" % (
                        data_structure["tcp_initial_rtt_estimate_ns"][1]
                    ))
                    f_config.write("tcp_connection_timeout_ns=%d\n" % data_structure["tcp_connection_timeout_ns"][1])
                    f_config.write("tcp_delayed_ack_timeout_ns=%d\n" % data_structure["tcp_delayed_ack_timeout_ns"][1])
                    f_config.write("tcp_persist_timeout_ns=%d\n" % data_structure["tcp_persist_timeout_ns"][1])

                # The point-to-point topology
                with open(run_dir_path + "/ptop_topology.properties", "w+") as f_topology:

                    # The leaf-spine
                    num_leafs = run_data_structure["num_leafs"][1]
                    num_spines = run_data_structure["num_spines"][1]
                    num_servers_per_leaf = run_data_structure["num_servers_per_leaf"][1]

                    # The leafs are 0, 1, ..., num_leafs - 1
                    # The spines are num_leafs, num_leafs + 1, ..., num_leafs + num_spines - 1
                    # The servers are num_leafs + num_spines, ..., num_leafs + num_spines + num_leafs * servers/leaf
                    links = []
                    for leaf in range(num_leafs):
                        from_id = leaf

                        # Connect each leaf to every spine
                        for spine in range(num_spines):
                            to_id = num_leafs + spine
                            links.append((from_id, to_id))

                        # Connect each leaf to its servers
                        for server in range(num_servers_per_leaf):
                            to_id = num_leafs + num_spines + leaf * num_servers_per_leaf + server
                            links.append((from_id, to_id))

                    # Finally write it all
                    f_topology.write("num_nodes=%d\n" % (num_leafs + num_spines + num_leafs * num_servers_per_leaf))
                    f_topology.write("num_undirected_edges=%d\n" % (
                            num_leafs * num_spines + num_leafs * num_servers_per_leaf
                    ))
                    f_topology.write("switches=set(%s)\n" % (
                        ','.join(str(x) for x in list(range(0, num_leafs + num_spines)))
                    ))
                    f_topology.write("switches_which_are_tors=set(%s)\n" % (
                        ','.join(str(x) for x in list(range(num_leafs)))
                    ))
                    f_topology.write("servers=set(%s)\n" % (
                        ','.join(str(x) for x in list(range(
                            num_leafs + num_spines, num_leafs + num_spines + num_leafs * num_servers_per_leaf
                        )))
                    ))
                    f_topology.write("undirected_edges=set(%s)\n" % (
                        ','.join(str(x[0]) + "-" + str(x[1]) for x in links)
                    ))
                    f_topology.write("link_channel_delay_ns=%s\n"
                                     % run_data_structure["link_channel_delay_ns"][1])
                    f_topology.write("link_net_device_data_rate_megabit_per_s=%.10f\n"
                                     % run_data_structure["link_net_device_data_rate_megabit_per_s"][1])
                    f_topology.write("link_net_device_queue=%s\n"
                                     % run_data_structure["link_net_device_queue"][1])
                    f_topology.write("link_net_device_receive_error_model=%s\n"
                                     % run_data_structure["link_net_device_receive_error_model"][1])
                    f_topology.write("link_interface_traffic_control_qdisc=%s\n"
                                     % run_data_structure["link_interface_traffic_control_qdisc"][1])

                # TCP flow schedule

                # Core values
                expected_flows_per_s = lambda_arrival_rate
                random.seed(run_master_seed)
                seed_start_times = random.randint(0, 100000000)
                seed_from_to = random.randint(0, 100000000)
                seed_flow_size = random.randint(0, 100000000)

                # Start times (ns)
                list_start_time_ns = draw_poisson_inter_arrival_gap_start_times_ns(
                    duration_ns, expected_flows_per_s, seed_start_times
                )
                num_starts = len(list_start_time_ns)

                # (From, to) tuples
                list_from_to = draw_n_times_from_to_all_to_all(
                    num_starts,
                    list(range(num_leafs + num_spines, num_leafs + num_spines + num_leafs * num_servers_per_leaf)),
                    seed_from_to
                )

                # Flow sizes in byte
                list_flow_size_byte = []
                random.seed(seed_flow_size)
                small_flow_size_byte = run_data_structure["small_flow_size_byte"][1]
                large_flow_size_byte = run_data_structure["large_flow_size_byte"][1]
                small_flow_probability = run_data_structure["small_flow_probability"][1]
                small_flow_priority = run_data_structure["small_flow_priority"][1]
                for i in range(len(list_start_time_ns)):
                    uniform_val = random.random()  # in [0, 1)
                    if uniform_val <= small_flow_probability:
                        list_flow_size_byte.append(small_flow_size_byte)
                    else:
                        list_flow_size_byte.append(large_flow_size_byte)

                # Finally, write the schedule
                with open(run_dir_path + "/tcp_flow_schedule.csv", "w+") as f_tcp_flow_schedule:
                    for i in range(len(list_start_time_ns)):
                        if list_flow_size_byte[i] == small_flow_size_byte:
                            priority = small_flow_priority
                        else:
                            priority = "low"
                        f_tcp_flow_schedule.write("%d,%d,%d,%d,%d,%s,\n" % (
                            i,
                            list_from_to[i][0],
                            list_from_to[i][1],
                            list_flow_size_byte[i],
                            list_start_time_ns[i],
                            priority
                        ))

                # Write that it is ready to be run
                with open(run_dir_path + "/input-ready.txt", "w+") as f_out:
                    f_out.write("Yes")

        # Return the list of run directory names (which is just one)
        return list_run_dir_names

    def generate_run_sh_body_for_run_dir(self, relative_runs_path_from_core_path, run_dir_name):
        run_sh_body = ""
        run_sh_body += "\n"
        run_sh_body += "# If the run has already been run before, it can be skipped\n"
        run_sh_body += "if [ -f \"%s/%s/logs_ns3/finished.txt\" ] && " \
                       "[ $(< \"%s/%s/logs_ns3/finished.txt\") == \"Yes\" ] ; then\n" \
                       % (
                           relative_runs_path_from_core_path, run_dir_name,
                           relative_runs_path_from_core_path, run_dir_name
                       )
        run_sh_body += "    exit 0\n"
        run_sh_body += "fi\n"
        run_sh_body += "\n"
        run_sh_body += "# Perform the run\n"
        run_sh_body += "cd frameworks/ns-3-bs/ns-3 || exit 1\n"
        run_sh_body += "./waf --run=\"main-full-pfifo-protocol --run_dir='../../../%s/%s'\" || exit 1\n" % (
            relative_runs_path_from_core_path, run_dir_name
        )
        return run_sh_body


class LoadLeafSpineRootClassPlotter(RootClassPlotter):

    def __init__(self):
        self.root_class_name = "load-ls"

    def get_root_class_name(self):
        return self.root_class_name

    def plot_for_experiment(
            self,
            exp_instance_name,
            path_to_core,
            list_run_dir_paths_from_core,
            experiment_plots_path_from_core,
            list_expinclude_filenames
    ):

        # Check that all run directories are finished
        for run_dir_path_from_core in list_run_dir_paths_from_core:
            run_dir = path_to_core + "/" + run_dir_path_from_core
            if not os.path.exists(run_dir + "/logs_ns3/finished.txt"):
                raise InvalidRunDirError(exp_instance_name, run_dir, "Run has not been run")
            with open(run_dir + "/logs_ns3/finished.txt", "r") as f_in:
                if f_in.read().strip() != "Yes":
                    raise InvalidRunDirError(exp_instance_name, run_dir, "Run is not finished")

        # Run directories into two categories and all run data structures
        list_run_dirs_equal = []
        list_run_dirs_prioritized = []
        all_run_data_structures = []
        for run_dir_path_from_core in list_run_dir_paths_from_core:
            run_dir = path_to_core + "/" + run_dir_path_from_core
            with open(run_dir + "/data-structure.txt", "r") as f_in:
                run_data_structure = ast.literal_eval(f_in.read())
                all_run_data_structures.append(run_data_structure)
                if run_data_structure["small_flow_priority"][1] == "low":
                    list_run_dirs_equal.append(run_dir)
                else:
                    list_run_dirs_prioritized.append(run_dir)

        # Parameters which are the same across all runs
        num_leafs = all_run_data_structures[0]["num_leafs"][1]
        num_spines = all_run_data_structures[0]["num_spines"][1]
        small_flow_size_byte = all_run_data_structures[0]["small_flow_size_byte"][1]
        large_flow_size_byte = all_run_data_structures[0]["large_flow_size_byte"][1]
        small_flow_probability = all_run_data_structures[0]["small_flow_probability"][1]
        cool_down_ns = all_run_data_structures[0]["cool_down_ns"][1]
        expected_mean_flow_size_byte = calculate_mean_flow_size_byte_from_data_structure(all_run_data_structures[0])
        spine_id_list = list(range(num_leafs, num_leafs + num_spines))

        # Parameters which differ
        set_load_with_lambda_flow_arrival_rate = set()
        for run_data_structure in all_run_data_structures:
            set_load_with_lambda_flow_arrival_rate.add(run_data_structure["load_with_lambda_flow_arrival_rate"][1])
        list_load_with_lambda_flow_arrival_rates = sorted(list(set_load_with_lambda_flow_arrival_rate), reverse=False)

        # Generate important statistics for the two categories
        flow_size_groups = [("small", small_flow_size_byte), ("large", large_flow_size_byte)]
        for val in [("data-equal", list_run_dirs_equal), ("data-prioritized", list_run_dirs_prioritized)]:
            gen_basic_sim_tcp_flows_plot_data(
                path_to_core + "/" + experiment_plots_path_from_core, val[0], val[1], flow_size_groups
            )
            gen_basic_sim_utilization_plot_data(
                path_to_core + "/" + experiment_plots_path_from_core, val[0], val[1], spine_id_list
            )

        # Generate the plots
        for filename_plot in list_expinclude_filenames:

            if filename_plot == "bottleneck-Mbps.txt":
                with open(path_to_core + "/" + experiment_plots_path_from_core + "/" + filename_plot, "w+") as f_out:
                    f_out.write("%g" % calculate_all_to_all_max_load_from_data_structure(all_run_data_structures[0]))
                continue

            if filename_plot == "lambda-lowest.txt":
                with open(path_to_core + "/" + experiment_plots_path_from_core + "/" + filename_plot, "w+") as f_out:
                    f_out.write("%.0f" % list_load_with_lambda_flow_arrival_rates[0][1])
                continue

            elif filename_plot == "lambda-highest.txt":
                with open(path_to_core + "/" + experiment_plots_path_from_core + "/" + filename_plot, "w+") as f_out:
                    f_out.write("%.0f" % list_load_with_lambda_flow_arrival_rates[-1][1])
                continue

            elif filename_plot == "lambda-step.txt":
                gap = list_load_with_lambda_flow_arrival_rates[1][1] - list_load_with_lambda_flow_arrival_rates[0][1]
                with open(path_to_core + "/" + experiment_plots_path_from_core + "/" + filename_plot, "w+") as f_out:
                    f_out.write("%.0f" % gap)
                continue

            elif filename_plot == "cool-down-s.txt":
                with open(path_to_core + "/" + experiment_plots_path_from_core + "/" + filename_plot, "w+") as f_out:
                    f_out.write("%.1f" % (cool_down_ns / 1000000000.0))
                continue

            elif filename_plot == "mean-flow-size.txt":
                flow_size_str = "%g~KB" % (expected_mean_flow_size_byte / 1000.0)
                if expected_mean_flow_size_byte > 1000000:
                    flow_size_str = "%g~MB" % (expected_mean_flow_size_byte / 1000000.0)
                with open(path_to_core + "/" + experiment_plots_path_from_core + "/" + filename_plot, "w+") as f_out:
                    f_out.write(flow_size_str)
                continue

            elif filename_plot == "small-flow-size-total-percentage.txt":
                with open(path_to_core + "/" + experiment_plots_path_from_core + "/" + filename_plot, "w+") as f_out:
                    f_out.write("%.0f" % (
                            100.0 *
                            (small_flow_size_byte * small_flow_probability) /
                            (
                                    small_flow_size_byte * small_flow_probability
                                    + large_flow_size_byte * (1.0 - small_flow_probability)
                            )
                    ))
                continue

            elif filename_plot == "large-flow-size-total-percentage.txt":
                with open(path_to_core + "/" + experiment_plots_path_from_core + "/" + filename_plot, "w+") as f_out:
                    f_out.write("%.0f" % (
                            100.0 *
                            (large_flow_size_byte * (1.0 - small_flow_probability)) /
                            (
                                    small_flow_size_byte * small_flow_probability
                                    + large_flow_size_byte * (1.0 - small_flow_probability)
                            )
                    ))
                continue

            elif filename_plot == "large-flow-size-divided-small-flow-size.txt":
                with open(path_to_core + "/" + experiment_plots_path_from_core + "/" + filename_plot, "w+") as f_out:
                    f_out.write("%.1f" % (float(large_flow_size_byte) / float(small_flow_size_byte)))
                continue

            elif filename_plot == "ratio-small-large-flows.txt":
                with open(path_to_core + "/" + experiment_plots_path_from_core + "/" + filename_plot, "w+") as f_out:
                    f_out.write("1:%d" % (small_flow_probability / (1.0 - small_flow_probability)))
                continue

            result_single = re.match(
                r'lambda-([0-9]+).txt',
                filename_plot
            )
            if result_single is not None:
                subgroups = result_single.groups()
                target_load = int(subgroups[0])
                respective_flow_arrival_rate = -1
                for found_load, f in list_load_with_lambda_flow_arrival_rates:
                    if found_load == target_load:
                        respective_flow_arrival_rate = f
                if respective_flow_arrival_rate == -1:
                    raise ValueError("Invalid target load: " + str(target_load))
                with open(path_to_core + "/" + experiment_plots_path_from_core + "/" + filename_plot, "w+") as f_out:
                    f_out.write("%.0f" % respective_flow_arrival_rate)
                continue

            result_single = re.match(
                r'load-([0-9]+)-(equal|prioritized)-vs-(equal|prioritized)-([^.]*)\.txt',
                filename_plot
            )
            if result_single is not None:
                subgroups = result_single.groups()
                target_load = int(subgroups[0])
                equal_or_prioritized_1 = subgroups[1]
                equal_or_prioritized_2 = subgroups[2]
                statistics_name_with_dashes = subgroups[3]

                data_filename = None

                # FCT plots
                # Examples:
                #   load-20-equal-vs-prioritized-all-fct-max.txt
                #   load-20-equal-vs-prioritized-all-fct-90th-percentile.txt
                result_single = re.match(
                    r'(all|small|large)-fct-([^.]*)',
                    statistics_name_with_dashes
                )
                if result_single is not None:
                    subgroups = result_single.groups()
                    all_or_small_or_large = subgroups[0]
                    statistic = subgroups[1]
                    data_filename = all_or_small_or_large + "_fct_ns_" + statistic.replace("-", "_")

                # Throughput plots
                # Examples:
                #   load-20-equal-vs-prioritized-all-throughput-max.txt
                #   load-20-equal-vs-prioritized-all-throughput-90th-percentile.txt
                result_single = re.match(
                    r'(all|small|large)-throughput-([^.]*)',
                    statistics_name_with_dashes
                )
                if result_single is not None:
                    subgroups = result_single.groups()
                    all_or_small_or_large = subgroups[0]
                    statistic = subgroups[1]
                    data_filename = (
                            all_or_small_or_large + "_avg_throughput_megabit_per_s_" + statistic.replace("-", "_")
                    )

                # Utilization plots
                # Examples:
                #   load-20-equal-vs-prioritized-leaf-spine-utilization-max.txt
                #   load-20-equal-vs-prioritized-all-throughput-percentile.txt
                result_single = re.match(
                    r'(server-leaf|leaf-spine)-utilization-([^.]*)',
                    statistics_name_with_dashes
                )
                if result_single is not None:
                    subgroups = result_single.groups()
                    server_leaf_or_leaf_spine = subgroups[0]
                    statistic = subgroups[1]
                    data_filename = (
                            server_leaf_or_leaf_spine.replace("-", "_") + "_link_utilization_fraction_"
                            + statistic.replace("-", "_")
                    )

                if data_filename is None:
                    raise PlotExpincludeError(
                        exp_instance_name, filename_plot,
                        "Statistic does not exist: " + statistics_name_with_dashes
                    )

                mean_statistic_value1 = get_mean_statistic(
                    exp_instance_name,
                    filename_plot,
                    target_load,
                    path_to_core + "/" + experiment_plots_path_from_core +
                    "/data-" + equal_or_prioritized_1 + "/" + data_filename + ".csv",
                    )

                mean_statistic_value2 = get_mean_statistic(
                    exp_instance_name,
                    filename_plot,
                    target_load,
                    path_to_core + "/" + experiment_plots_path_from_core +
                    "/data-" + equal_or_prioritized_2 + "/" + data_filename + ".csv",
                    )

                # Finally, write the output plot file
                with open(path_to_core + "/" + experiment_plots_path_from_core + "/" + filename_plot, "w+") as f_out:
                    f_out.write("%.2g" % (float(mean_statistic_value1) / float(mean_statistic_value2)))

                continue

            result_single = re.match(
                r'load-([0-9]+)-vs-([0-9]+)-(equal|prioritized)-([^.]*)\.txt',
                filename_plot
            )
            if result_single is not None:
                subgroups = result_single.groups()
                target_load_1 = int(subgroups[0])
                target_load_2 = int(subgroups[1])
                equal_or_prioritized = subgroups[2]
                statistics_name_with_dashes = subgroups[3]

                data_filename = None

                # FCT plots
                # Examples:
                #   load-20-vs-30-equal-all-fct-max.txt
                #   load-20-vs-30-equal-all-fct-90th-percentile.txt
                result_single = re.match(
                    r'(all|small|large)-fct-([^.]*)',
                    statistics_name_with_dashes
                )
                if result_single is not None:
                    subgroups = result_single.groups()
                    all_or_small_or_large = subgroups[0]
                    statistic = subgroups[1]
                    data_filename = all_or_small_or_large + "_fct_ns_" + statistic.replace("-", "_")

                # Throughput plots
                # Examples:
                #   load-20-vs-30-equal-all-throughput-max.txt
                #   load-20-vs-30-equal-all-throughput-90th-percentile.txt
                result_single = re.match(
                    r'(all|small|large)-throughput-([^.]*)',
                    statistics_name_with_dashes
                )
                if result_single is not None:
                    subgroups = result_single.groups()
                    all_or_small_or_large = subgroups[0]
                    statistic = subgroups[1]
                    data_filename = (
                            all_or_small_or_large + "_avg_throughput_megabit_per_s_" + statistic.replace("-", "_")
                    )

                # Utilization plots
                # Examples:
                #   load-20-vs-30-equal-leaf-spine-utilization-max.txt
                #   load-20-vs-30-equal-all-throughput-percentile.txt
                result_single = re.match(
                    r'(server-leaf|leaf-spine)-utilization-([^.]*)',
                    statistics_name_with_dashes
                )
                if result_single is not None:
                    subgroups = result_single.groups()
                    server_leaf_or_leaf_spine = subgroups[0]
                    statistic = subgroups[1]
                    data_filename = (
                            server_leaf_or_leaf_spine.replace("-", "_") + "_link_utilization_fraction_"
                            + statistic.replace("-", "_")
                    )

                if data_filename is None:
                    raise PlotExpincludeError(
                        exp_instance_name, filename_plot,
                        "Statistic does not exist"
                    )

                mean_statistic_value1 = get_mean_statistic(
                    exp_instance_name,
                    filename_plot,
                    target_load_1,
                    path_to_core + "/" + experiment_plots_path_from_core +
                    "/data-" + equal_or_prioritized + "/" + data_filename + ".csv",
                    )

                mean_statistic_value2 = get_mean_statistic(
                    exp_instance_name,
                    filename_plot,
                    target_load_2,
                    path_to_core + "/" + experiment_plots_path_from_core +
                    "/data-" + equal_or_prioritized + "/" + data_filename + ".csv",
                    )

                # Finally, write the output plot file
                with open(path_to_core + "/" + experiment_plots_path_from_core + "/" + filename_plot, "w+") as f_out:
                    f_out.write("%.2g" % (float(mean_statistic_value1) / float(mean_statistic_value2)))

                continue

            result_single = re.match(
                r'load-([0-9]+)-(equal|prioritized)-([^.]*)\.txt',
                filename_plot
            )
            if result_single is not None:
                subgroups = result_single.groups()
                target_load = int(subgroups[0])
                equal_or_prioritized = subgroups[1]
                statistics_name_with_dashes = subgroups[2]

                def write_fct_as_unit(fct_ns, arg_unit):
                    if arg_unit == "ms":
                        return "%.2f" % fct_ns / 1000000.0
                    else:
                        raise ValueError("Unknown unit: " + arg_unit)

                def write_throughput_as_unit(throughput_megabit_per_s, arg_unit):
                    if arg_unit == "Mbps":
                        return "%.2f" % throughput_megabit_per_s
                    else:
                        raise ValueError("Unknown unit: " + arg_unit)

                def write_utilization_as_percentage(utilization_fraction, arg_unit):
                    if arg_unit == "percentage":
                        return "%d" % int(round(utilization_fraction * 100.0))
                    else:
                        raise ValueError("Unknown unit: " + arg_unit)

                unit = None
                data_filename = None
                final_formatter = None

                # FCT plots
                # Examples:
                #   load-20-equal-all-throughput-Mbps-max.txt
                #   load-20-equal-large-throughput-Mbps-90th-percentile.txt
                result_single = re.match(
                    r'(all|small|large)-fct-([^\-]*)-([^.]*)',
                    statistics_name_with_dashes
                )
                if result_single is not None:
                    subgroups = result_single.groups()
                    all_or_small_or_large = subgroups[0]
                    unit = subgroups[1]
                    statistic = subgroups[2]
                    final_formatter = write_fct_as_unit
                    data_filename = all_or_small_or_large + "_fct_ns_" + statistic.replace("-", "_")

                # Throughput plots
                # Examples:
                #   load-20-equal-small-throughput-Mbps-max.txt
                #   load-20-equal-all-throughput-Mbps-90th-percentile.txt
                result_single = re.match(
                    r'(all|small|large)-throughput-([^\-]*)-([^.]*)',
                    statistics_name_with_dashes
                )
                if result_single is not None:
                    subgroups = result_single.groups()
                    all_or_small_or_large = subgroups[0]
                    unit = subgroups[1]
                    statistic = subgroups[2]
                    final_formatter = write_throughput_as_unit
                    data_filename = (
                            all_or_small_or_large + "_avg_throughput_megabit_per_s_" + statistic.replace("-", "_")
                    )

                # Utilization plots
                # Examples:
                #   load-20-equal-leaf-spine-utilization-max.txt
                #   load-20-equal-server-leaf-throughput-Mbps-90th-percentile.txt
                result_single = re.match(
                    r'(server-leaf|leaf-spine)-utilization-([^.]*)',
                    statistics_name_with_dashes
                )
                if result_single is not None:
                    subgroups = result_single.groups()
                    server_leaf_or_leaf_spine = subgroups[0]
                    unit = "percentage"
                    statistic = subgroups[1]
                    final_formatter = write_utilization_as_percentage
                    data_filename = (
                            server_leaf_or_leaf_spine.replace("-", "_") + "_link_utilization_fraction_"
                            + statistic.replace("-", "_")
                    )

                if unit is None or data_filename is None or final_formatter is None:
                    raise PlotExpincludeError(
                        exp_instance_name, filename_plot,
                        "Statistic does not exist"
                    )

                mean_statistic_value = get_mean_statistic(
                    exp_instance_name,
                    filename_plot,
                    target_load,
                    path_to_core + "/" + experiment_plots_path_from_core +
                    "/data-" + equal_or_prioritized + "/" + data_filename + ".csv",
                )

                # Finally, write the output plot file
                with open(path_to_core + "/" + experiment_plots_path_from_core + "/" + filename_plot, "w+") as f_out:
                    f_out.write(final_formatter(mean_statistic_value, unit))

                continue

            # Determine line color
            color_line1 = "1"
            color_line2 = "4"
            title_line1 = "Equal"
            title_line2 = "Small Prioritized"

            # plot_target_load_vs_tcp_flows_(small/large)_fct_ns_(METRIC).pdf
            result_single = re.match(
                r'plot_target_load_vs_tcp_flows_(small|large)_fct_ns_(.*).pdf',
                filename_plot
            )

            if result_single is not None:
                subgroups = result_single.groups()
                flow_size_group = subgroups[0]
                metric = subgroups[1]

                # No title
                title = ""

                # Determine x-axis label
                metric_y_label = metric  # Default
                key_position = "top left"
                if metric == "99th_percentile":
                    metric_y_label = "99th %-tile FCT (ms)"
                    if flow_size_group == "small":
                        key_position = "at 65,220"
                elif metric == "99_9th_percentile":
                    metric_y_label = "99.9th %-tile FCT (ms)"
                elif metric == "average":
                    metric_y_label = "Average FCT (ms)"

                # Perform the plot
                local_shell = exputil.LocalShell()
                pdf_filename = "%s/%s/%s" % (
                    path_to_core,
                    experiment_plots_path_from_core,
                    filename_plot
                )
                data_filename1 = "%s/%s/%s" % (
                    path_to_core,
                    experiment_plots_path_from_core,
                    "data-equal/%s_fct_ns_%s.csv" % (flow_size_group, metric)
                )
                data_filename2 = "%s/%s/%s" % (
                    path_to_core,
                    experiment_plots_path_from_core,
                    "data-prioritized/%s_fct_ns_%s.csv" % (flow_size_group, metric)
                )
                local_shell.copy_file(
                    "%s/experimentex/rootclasses/gnuplot/plot-target-load-vs-fct-metric.plt" % path_to_core,
                    "temp.plt"
                )
                local_shell.sed_replace_in_file_plain("temp.plt", "[METRIC]", metric_y_label)
                local_shell.sed_replace_in_file_plain("temp.plt", "[TITLE]", title)
                local_shell.sed_replace_in_file_plain("temp.plt", "[OUTPUT-FILE]", pdf_filename)
                local_shell.sed_replace_in_file_plain("temp.plt", "[DATA-FILE1]", data_filename1)
                local_shell.sed_replace_in_file_plain("temp.plt", "[DATA-FILE2]", data_filename2)
                local_shell.sed_replace_in_file_plain("temp.plt", "[COLOR-LINE1]", color_line1)
                local_shell.sed_replace_in_file_plain("temp.plt", "[COLOR-LINE2]", color_line2)
                local_shell.sed_replace_in_file_plain("temp.plt", "[TITLE-LINE1]", title_line1)
                local_shell.sed_replace_in_file_plain("temp.plt", "[TITLE-LINE2]", title_line2)
                local_shell.sed_replace_in_file_plain("temp.plt", "[KEY-POSITION]", key_position)
                local_shell.perfect_exec("gnuplot temp.plt")
                local_shell.remove("temp.plt")

                # Crop the final pdf to make it have less whitespace around it
                local_shell.perfect_exec("pdfcrop " + pdf_filename + " " + pdf_filename)

                continue

            # plot_target_load_vs_tcp_flows_(small/large)_fraction_completed.pdf
            result_single = re.match(
                r'plot_target_load_vs_tcp_flows_(small|large)_fraction_completed.pdf',
                filename_plot
            )

            if result_single is not None:
                subgroups = result_single.groups()
                flow_size_group = subgroups[0]
                metric = "fraction_completed"

                # No title
                title = ""

                # Determine x-axis label
                metric_y_label = "Fraction completed"

                # Perform the plot
                local_shell = exputil.LocalShell()
                pdf_filename = "%s/%s/%s" % (
                    path_to_core,
                    experiment_plots_path_from_core,
                    filename_plot
                )
                data_filename1 = "%s/%s/%s" % (
                    path_to_core,
                    experiment_plots_path_from_core,
                    "data-equal/%s_%s.csv" % (flow_size_group, metric)
                )
                data_filename2 = "%s/%s/%s" % (
                    path_to_core,
                    experiment_plots_path_from_core,
                    "data-prioritized/%s_%s.csv" % (flow_size_group, metric)
                )
                local_shell.copy_file(
                    "%s/experimentex/rootclasses/gnuplot/plot-target-load-vs-completion-metric.plt" % path_to_core,
                    "temp.plt"
                )
                local_shell.sed_replace_in_file_plain("temp.plt", "[METRIC]", metric_y_label)
                local_shell.sed_replace_in_file_plain("temp.plt", "[TITLE]", title)
                local_shell.sed_replace_in_file_plain("temp.plt", "[OUTPUT-FILE]", pdf_filename)
                local_shell.sed_replace_in_file_plain("temp.plt", "[DATA-FILE1]", data_filename1)
                local_shell.sed_replace_in_file_plain("temp.plt", "[DATA-FILE2]", data_filename2)
                local_shell.sed_replace_in_file_plain("temp.plt", "[COLOR-LINE1]", color_line1)
                local_shell.sed_replace_in_file_plain("temp.plt", "[COLOR-LINE2]", color_line2)
                local_shell.sed_replace_in_file_plain("temp.plt", "[TITLE-LINE1]", title_line1)
                local_shell.sed_replace_in_file_plain("temp.plt", "[TITLE-LINE2]", title_line2)
                local_shell.perfect_exec("gnuplot temp.plt")
                local_shell.remove("temp.plt")

                # Crop the final pdf to make it have less whitespace around it
                local_shell.perfect_exec("pdfcrop " + pdf_filename + " " + pdf_filename)

                continue

            # plot_target_load_vs_tcp_flows_(small/large)_avg_throughput_megabit_per_s_(METRIC).pdf
            result_single = re.match(
                r'plot_target_load_vs_tcp_flows_(small|large)_avg_throughput_megabit_per_s_(.*).pdf',
                filename_plot
            )

            if result_single is not None:
                subgroups = result_single.groups()
                flow_size_group = subgroups[0]
                metric = subgroups[1]

                # No title
                title = ""

                # Determine x-axis label
                metric_y_label = metric  # Default
                key_position = "top right"
                if metric == "average":
                    metric_y_label = "Average rate (Mbit/s)"
                    key_position = "bottom left"
                elif metric == "1th_percentile":
                    metric_y_label = "1^{th} %-tile rate (Mbit/s)"
                elif metric == "0_1th_percentile":
                    metric_y_label = "0.1th %-tile rate (Mbit/s)"

                # Perform the plot
                local_shell = exputil.LocalShell()
                pdf_filename = "%s/%s/%s" % (path_to_core, experiment_plots_path_from_core, filename_plot)
                data_filename1 = "%s/%s/%s" % (
                    path_to_core,
                    experiment_plots_path_from_core,
                    "data-equal/%s_avg_throughput_megabit_per_s_%s.csv" % (flow_size_group, metric)
                )
                data_filename2 = "%s/%s/%s" % (
                    path_to_core,
                    experiment_plots_path_from_core,
                    "data-prioritized/%s_avg_throughput_megabit_per_s_%s.csv" % (flow_size_group, metric)
                )
                local_shell.copy_file(
                    "%s/experimentex/rootclasses/gnuplot/plot-target-load-vs-throughput-metric.plt" % path_to_core,
                    "temp.plt"
                )
                local_shell.sed_replace_in_file_plain("temp.plt", "[METRIC]", metric_y_label)
                local_shell.sed_replace_in_file_plain("temp.plt", "[TITLE]", title)
                local_shell.sed_replace_in_file_plain("temp.plt", "[OUTPUT-FILE]", pdf_filename)
                local_shell.sed_replace_in_file_plain("temp.plt", "[DATA-FILE1]", data_filename1)
                local_shell.sed_replace_in_file_plain("temp.plt", "[DATA-FILE2]", data_filename2)
                local_shell.sed_replace_in_file_plain("temp.plt", "[COLOR-LINE1]", color_line1)
                local_shell.sed_replace_in_file_plain("temp.plt", "[COLOR-LINE2]", color_line2)
                local_shell.sed_replace_in_file_plain("temp.plt", "[TITLE-LINE1]", title_line1)
                local_shell.sed_replace_in_file_plain("temp.plt", "[TITLE-LINE2]", title_line2)
                local_shell.sed_replace_in_file_plain("temp.plt", "[KEY-POSITION]", key_position)
                local_shell.perfect_exec("gnuplot temp.plt")
                local_shell.remove("temp.plt")

                # Crop the final pdf to make it have less whitespace around it
                local_shell.perfect_exec("pdfcrop " + pdf_filename + " " + pdf_filename)

                continue

            # plot_target_load_vs_leaf_spine_link_utilization_fraction_max
            result_single = re.match(
                r'plot_target_load_vs_(.*)_link_utilization_fraction_(.*).pdf',
                filename_plot
            )

            if result_single is not None:
                subgroups = result_single.groups()
                group = subgroups[0]
                metric = subgroups[1]

                # Perform the plot
                local_shell = exputil.LocalShell()
                pdf_filename = "%s/%s/%s" % (path_to_core, experiment_plots_path_from_core, filename_plot)
                data_filename1 = "%s/%s/%s" % (
                    path_to_core,
                    experiment_plots_path_from_core,
                    "data-equal/%s_link_utilization_fraction_%s.csv" % (group, metric)
                )
                data_filename2 = "%s/%s/%s" % (
                    path_to_core,
                    experiment_plots_path_from_core,
                    "data-prioritized/%s_link_utilization_fraction_%s.csv" % (group, metric)
                )
                local_shell.copy_file(
                    "%s/experimentex/rootclasses/gnuplot/plot-target-load-vs-utilization-fraction-metric.plt"
                    % path_to_core,
                    "temp.plt"
                )
                local_shell.sed_replace_in_file_plain("temp.plt", "[OUTPUT-FILE]", pdf_filename)
                local_shell.sed_replace_in_file_plain("temp.plt", "[DATA-FILE1]", data_filename1)
                local_shell.sed_replace_in_file_plain("temp.plt", "[DATA-FILE2]", data_filename2)
                local_shell.sed_replace_in_file_plain("temp.plt", "[COLOR-LINE1]", color_line1)
                local_shell.sed_replace_in_file_plain("temp.plt", "[COLOR-LINE2]", color_line2)
                local_shell.sed_replace_in_file_plain("temp.plt", "[TITLE-LINE1]", title_line1)
                local_shell.sed_replace_in_file_plain("temp.plt", "[TITLE-LINE2]", title_line2)
                local_shell.perfect_exec("gnuplot temp.plt")
                local_shell.remove("temp.plt")

                # Crop the final pdf to make it have less whitespace around it
                local_shell.perfect_exec("pdfcrop " + pdf_filename + " " + pdf_filename)

                continue

            raise PlotExpincludeError(exp_instance_name, filename_plot, "Unknown plot filename")
