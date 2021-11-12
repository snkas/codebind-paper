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

import exputil
import os
from hashlib import sha256
import math
import numpy as np
from exputil import PropertiesConfig
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
    flatten_brace_group_to_str
)

# Import some common network argument parsing utilities
from .helper.utilityunitparser import (
    parse_congestion_protocol
)

from .helper.bsincorporators import (
    incorporator_experiment_duration,
    incorporator_link_channel_and_network_devices,
    incorporator_qdisc_red,
    incorporate_tcp_settings_using_identifier,
    incorporator_buffer_size,
    incorporator_delayed_ack
)

from .helper.tcpflowplotter import (
    plot_tcp_flow
)


class OneLinkTcpRootClassInterpreter(RootClassInterpreter):

    def __init__(self):
        self.root_class_name = "one-link-tcp"

    def get_root_class_name(self):
        return self.root_class_name

    def generate_empty_experiment_data_structure(self):
        return {
            "duration_ns": (False, None),  # Integer > 0
            "link_channel_delay_ns": (False, None),  # Integer >= 0
            "link_net_device_data_rate_megabit_per_s": (False, None),  # Float > 0
            "link_net_device_queue": (False, None),  # String (e.g., "drop_tail(100p)")
            "link_net_device_receive_error_model": (False, None),  # String
                                                                   # (e.g., "none", "iid_uniform_random_pkt(0.001)")
            "link_interface_traffic_control_qdisc": (False, None),  # String (e.g., "disabled", "fifo(100p)")

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

        # Duration
        # Example:
        # The experiment is run for 20~seconds.
        if incorporator_experiment_duration(exp_name, expline_identifier, expline, data_structure):
            return data_structure

        # Link channel and network devices
        # Example:
        # Every/The link has the following properties: the channel has a delay of 10~$\mu s$, and its link network
        # devices have a data rate of 50~Mbit/s, 0.1\% random packet loss, and a FIFO queue of 100 packets.
        if incorporator_link_channel_and_network_devices(exp_name, expline_identifier, expline, data_structure):
            return data_structure

        # Qdisc RED
        # Example:
        # We set a random early detection (RED) queueing discipline with a maximum queue size
        # of 100 packets and a binary marking (or drop if the IP packet does not support ECN) threshold at 50 packets.
        if incorporator_qdisc_red(exp_name, expline_identifier, expline, data_structure):
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

        # Example:
        # TCP NewReno
        # TCP Vegas
        # TCP Cubic
        # DCTCP
        flattened_str = flatten_brace_group_to_str(expline)
        if (flattened_str == "TCP NewReno" or flattened_str == "TCP Cubic"
                or flattened_str == "TCP Vegas" or flattened_str == "DCTCP"):
            if data_structure["tcp_protocol"][0]:
                raise InterpretExplineError(exp_name, expline_identifier, expline, "Protocol is already set")
            data_structure["tcp_protocol"] = (
                True,
                parse_congestion_protocol(exp_name, expline_identifier, expline, flattened_str)
            )
            return data_structure

        # If nothing matched, then it failed
        raise InterpretExplineError(exp_name, expline_identifier, expline, "Did not match any pattern.")

    def generate_run_dirs_for_experiment_data_structure(self, exp_instance_name, runs_path, data_structure):

        # Check validity of data structure
        if not data_structure["duration_ns"][0]:
            raise RunDirGenerationError(exp_instance_name, "Duration is not set")
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

        # Calculate the hash of the data structure
        run_hash = sha256(repr(sorted(data_structure.items())).encode('utf-8')).hexdigest()

        # Create the run directory
        run_dir_name = self.root_class_name + "-" + str(run_hash)
        run_dir_path = runs_path + "/" + run_dir_name
        os.makedirs(run_dir_path, exist_ok=True)

        # Open the data-structure.txt file if it exists, and compare to make sure we don't
        # have a weird duplicate SHA-256 hash (unlikely, but could happen if the hashing
        # of the run data structure was done incorrectly)
        if os.path.exists(run_dir_path + "/data-structure.txt"):
            with open(run_dir_path + "/data-structure.txt", "r") as f_in:
                content = f_in.read()
                if content != str(data_structure):
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
                f_out.write(str(data_structure))

            # Run configuration
            with open(run_dir_path + "/config_ns3.properties", "w+") as f_config:
                f_config.write("simulation_end_time_ns=%d\n" % data_structure["duration_ns"][1])
                f_config.write("simulation_seed=123456789\n")
                f_config.write("topology_ptop_filename=\"ptop_topology.properties\"\n")
                f_config.write("enable_tcp_flow_scheduler=true\n")
                f_config.write("tcp_flow_schedule_filename=\"tcp_flow_schedule.csv\"\n")
                f_config.write("tcp_flow_enable_logging_for_tcp_flow_ids=all\n")
                f_config.write("tcp_protocol=%s\n" % data_structure["tcp_protocol"][1])
                f_config.write("tcp_config=custom\n")
                f_config.write("tcp_clock_granularity_ns=1000000\n")  # 1ms clock granularity
                f_config.write("tcp_snd_buf_size_byte=%d\n" % data_structure["tcp_snd_buf_size_byte"][1])
                f_config.write("tcp_rcv_buf_size_byte=%d\n" % data_structure["tcp_rcv_buf_size_byte"][1])
                f_config.write("tcp_init_cwnd_pkt=%d\n" % data_structure["tcp_init_cwnd_pkt"][1])
                f_config.write("tcp_segment_size_byte=%d\n" % data_structure["tcp_segment_size_byte"][1])
                f_config.write("tcp_opt_timestamp_enabled=%s\n" % data_structure["tcp_opt_timestamp_enabled"][1])
                f_config.write("tcp_opt_sack_enabled=%s\n" % data_structure["tcp_opt_sack_enabled"][1])
                f_config.write("tcp_opt_win_scaling_enabled=%s\n" % data_structure["tcp_opt_win_scaling_enabled"][1])
                f_config.write("tcp_opt_pacing_enabled=%s\n" % data_structure["tcp_opt_pacing_enabled"][1])
                f_config.write("tcp_delayed_ack_packet_count=%d\n" % data_structure["tcp_delayed_ack_packet_count"][1])
                f_config.write("tcp_no_delay=%s\n" % data_structure["tcp_no_delay"][1])
                f_config.write("tcp_max_seg_lifetime_ns=%d\n" % data_structure["tcp_max_seg_lifetime_ns"][1])
                f_config.write("tcp_min_rto_ns=%d\n" % data_structure["tcp_min_rto_ns"][1])
                f_config.write("tcp_initial_rtt_estimate_ns=%d\n" % data_structure["tcp_initial_rtt_estimate_ns"][1])
                f_config.write("tcp_connection_timeout_ns=%d\n" % data_structure["tcp_connection_timeout_ns"][1])
                f_config.write("tcp_delayed_ack_timeout_ns=%d\n" % data_structure["tcp_delayed_ack_timeout_ns"][1])
                f_config.write("tcp_persist_timeout_ns=%d\n" % data_structure["tcp_persist_timeout_ns"][1])

            # The point-to-point topology
            with open(run_dir_path + "/ptop_topology.properties", "w+") as f_topology:
                f_topology.write("num_nodes=2\n")
                f_topology.write("num_undirected_edges=1\n")
                f_topology.write("switches=set(0,1)\n")
                f_topology.write("switches_which_are_tors=set(0,1)\n")
                f_topology.write("servers=set()\n")
                f_topology.write("undirected_edges=set(0-1)\n")
                f_topology.write("link_channel_delay_ns=%s\n"
                                 % data_structure["link_channel_delay_ns"][1])
                f_topology.write("link_net_device_data_rate_megabit_per_s=%.10f\n"
                                 % data_structure["link_net_device_data_rate_megabit_per_s"][1])
                f_topology.write("link_net_device_queue=%s\n"
                                 % data_structure["link_net_device_queue"][1])
                f_topology.write("link_net_device_receive_error_model=%s\n"
                                 % data_structure["link_net_device_receive_error_model"][1])
                f_topology.write("link_interface_traffic_control_qdisc=%s\n"
                                 % data_structure["link_interface_traffic_control_qdisc"][1])

            # TCP flow schedule
            with open(run_dir_path + "/tcp_flow_schedule.csv", "w+") as f_tcp_flow_schedule:
                f_tcp_flow_schedule.write("0,0,1,10000000000,0,,\n")

            # Write that it is ready to be run
            with open(run_dir_path + "/input-ready.txt", "w+") as f_out:
                f_out.write("Yes")

        # Return the list of run directory names (which is just one)
        return [run_dir_name]

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
        run_sh_body += "./waf --run=\"main-full-with-protocol --run_dir='../../../%s/%s'\" || exit 1\n" % (
            relative_runs_path_from_core_path, run_dir_name
        )
        return run_sh_body


def calculate_bdp_pkt(ptop_topology_filename, segment_size_byte):
    properties = PropertiesConfig(ptop_topology_filename)
    link_channel_delay_ns = exputil.parse_positive_int(properties.get_property_or_fail("link_channel_delay_ns"))
    link_net_device_data_rate_megabit_per_s = exputil.parse_positive_float(properties.get_property_or_fail(
        "link_net_device_data_rate_megabit_per_s"
    ))
    bdp_byte = link_net_device_data_rate_megabit_per_s * link_channel_delay_ns * 2 * 0.000125
    # Header size is:
    # 2 (P2P) + 20 (IP) + 20 (TCP basic) + 12 (TCP option: timestamp: 10 -> in 4 byte steps so padded to 12)
    # = 54
    return int(math.ceil(bdp_byte / float(segment_size_byte + 54.0)))


def calculate_link_net_device_queue_pkt(ptop_topology_filename):
    properties = PropertiesConfig(ptop_topology_filename)
    link_net_device_queue_str = properties.get_property_or_fail("link_net_device_queue")
    return int(link_net_device_queue_str[10:-2])


def calculate_qdisc_threshold_pkt(ptop_topology_filename):
    properties = PropertiesConfig(ptop_topology_filename)
    qdisc_queue_str = properties.get_property_or_fail("link_interface_traffic_control_qdisc")
    return int(qdisc_queue_str.split(";")[3].strip())


class OneLinkTcpRootClassPlotter(RootClassPlotter):

    def __init__(self):
        self.root_class_name = "one-link-tcp"

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

        # There is only one run directory for this root class
        run_dir_path_from_core = list_run_dir_paths_from_core[0]
        with open(path_to_core + "/" + run_dir_path_from_core + "/data-structure.txt", "r") as f_in:
            run_data_structure = ast.literal_eval(f_in.read())

        # We plot everything for TCP flow with ID 0 (averaging rate on 1s time scale)
        plot_tcp_flow(
            path_to_core + "/" + run_dir_path_from_core + "/logs_ns3",
            path_to_core + "/experimentex/rootclasses/gnuplot",
            path_to_core + "/" + experiment_plots_path_from_core + "/data",
            path_to_core + "/" + experiment_plots_path_from_core,
            0,
            1000000000,
            run_data_structure["tcp_segment_size_byte"][1]
        )

        # Useful for many operations
        local_shell = exputil.LocalShell()

        # Generate the plots
        for filename_plot in list_expinclude_filenames:

            # TCP flow with ID 0 with congestion window, slow-start threshold, etc.
            if filename_plot == "plot_tcp_flow_time_vs_together_0.pdf":

                # Crop the final pdf to make it have less whitespace around it
                pdf_filename = path_to_core + "/" + experiment_plots_path_from_core + "/" + filename_plot
                local_shell.perfect_exec("pdfcrop " + pdf_filename + " " + pdf_filename)

            elif filename_plot == "plot_tcp_flow_time_vs_rate_0.pdf":

                # Crop the final pdf to make it have less whitespace around it
                pdf_filename = path_to_core + "/" + experiment_plots_path_from_core + "/" + filename_plot
                local_shell.perfect_exec("pdfcrop " + pdf_filename + " " + pdf_filename)

            elif filename_plot == "plot_tcp_flow_time_vs_rtt_0.pdf":

                # Crop the final pdf to make it have less whitespace around it
                pdf_filename = path_to_core + "/" + experiment_plots_path_from_core + "/" + filename_plot
                local_shell.perfect_exec("pdfcrop " + pdf_filename + " " + pdf_filename)

            elif filename_plot == "bdp-pkt.txt":
                bdp_pkt = calculate_bdp_pkt(
                    path_to_core + "/" + run_dir_path_from_core + "/ptop_topology.properties",
                    run_data_structure["tcp_segment_size_byte"][1]
                )
                with open(path_to_core + "/" + experiment_plots_path_from_core + "/" + filename_plot, "w+") as f_out:
                    f_out.write("%d packet%s" % (bdp_pkt, "" if bdp_pkt == 1 else "s"))

            elif filename_plot == "ndq-size-pkt.txt":
                link_net_device_queue_pkt = calculate_link_net_device_queue_pkt(
                    path_to_core + "/" + run_dir_path_from_core + "/ptop_topology.properties"
                )
                with open(path_to_core + "/" + experiment_plots_path_from_core + "/" + filename_plot, "w+") as f_out:
                    f_out.write(
                        "%d packet%s" % (
                            link_net_device_queue_pkt, "" if link_net_device_queue_pkt == 1 else "s"
                        )
                    )

            elif filename_plot == "qdisc-threshold-pkt.txt":
                qdisc_queue_pkt = calculate_qdisc_threshold_pkt(
                    path_to_core + "/" + run_dir_path_from_core + "/ptop_topology.properties"
                )
                with open(path_to_core + "/" + experiment_plots_path_from_core + "/" + filename_plot, "w+") as f_out:
                    f_out.write("%d packet%s" % (qdisc_queue_pkt, "" if qdisc_queue_pkt == 1 else "s"))

            elif filename_plot == "ndq-qdisc-bdp-pkt.txt":
                topology_ptop_filename = path_to_core + "/" + run_dir_path_from_core + "/ptop_topology.properties"

                bdp_pkt = calculate_bdp_pkt(topology_ptop_filename, run_data_structure["tcp_segment_size_byte"][1])
                link_net_device_queue_pkt = calculate_link_net_device_queue_pkt(topology_ptop_filename)
                qdisc_queue_pkt = calculate_qdisc_threshold_pkt(topology_ptop_filename)
                total_pkt = bdp_pkt + link_net_device_queue_pkt + qdisc_queue_pkt

                with open(path_to_core + "/" + experiment_plots_path_from_core + "/" + filename_plot, "w+") as f_out:
                    f_out.write("%d packet%s" % (total_pkt, "" if total_pkt == 1 else "s"))

            elif filename_plot == "average-rate-Mbps.txt":
                with open(path_to_core + "/" + run_dir_path_from_core + "/logs_ns3/tcp_flows.csv", "r") as f_in:
                    in_split = f_in.read().split(",")
                    rate_megabit_per_s = float(in_split[7]) / float(in_split[6]) * 8000.0
                with open(path_to_core + "/" + experiment_plots_path_from_core + "/" + filename_plot, "w+") as f_out:
                    f_out.write("%.2f" % rate_megabit_per_s)

            elif filename_plot == "average-rtt-ms.txt":
                entries = []
                with open(path_to_core + "/" + run_dir_path_from_core + "/logs_ns3/tcp_flow_0_rtt.csv", "r") as f_in:
                    for line in f_in:
                        entries.append(float(line.split(",")[2]))
                with open(path_to_core + "/" + experiment_plots_path_from_core + "/" + filename_plot, "w+") as f_out:
                    f_out.write("%.2f" % (np.average(entries) / 1000000.0))

            else:
                raise PlotExpincludeError(exp_instance_name, filename_plot, "Unknown plot filename")
