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

# Utility functions
from ..rootclassutility import (
    flatten_brace_group_to_str,
    expand_regex_to_be_tolerant_to_whitespace
)

# Import the abstract class for interpreter
from ..rootclassinterpreter import (
    InterpretExplineError,
)

# Import some common network argument parsing utilities
from .utilityunitparser import (
    parse_texish_percentage,
    parse_texish_data_rate_to_megabit_per_s,
    parse_texish_time_to_ns,
    parse_texish_data_to_byte,
)


def update_internal_param(exp_name, expline_identifier, expline, data_structure, param_key, param_value):
    if data_structure[param_key][0]:
        raise InterpretExplineError(exp_name, expline_identifier, expline, "%s is already set" % param_key)
    data_structure[param_key] = (True, param_value)


def parse_str_boolean(value):
    if value == "enabled":
        return "true"
    elif value == "disabled":
        return "false"
    raise ValueError("Invalid boolean value: " + value)


def incorporate_tcp_settings_using_identifier(exp_name, expline_identifier, expline, data_structure):

    # Use the identifier first if possible
    identifier_matched = True
    if expline_identifier == "snd-buf-size-byte":
        update_internal_param(
            exp_name, expline_identifier, expline, data_structure,
            "tcp_" + expline_identifier.replace("-", "_"),
            parse_texish_data_to_byte(exp_name, expline_identifier, expline, flatten_brace_group_to_str(expline))
        )

    elif expline_identifier == "rcv-buf-size-byte":
        update_internal_param(
            exp_name, expline_identifier, expline, data_structure,
            "tcp_" + expline_identifier.replace("-", "_"),
            parse_texish_data_to_byte(exp_name, expline_identifier, expline, flatten_brace_group_to_str(expline))
        )

    elif expline_identifier == "init-cwnd-pkt":
        update_internal_param(
            exp_name, expline_identifier, expline, data_structure,
            "tcp_" + expline_identifier.replace("-", "_"),
            exputil.parse_positive_int(flatten_brace_group_to_str(expline))
        )

    elif expline_identifier == "segment-size":
        update_internal_param(
            exp_name, expline_identifier, expline, data_structure,
            "tcp_" + expline_identifier.replace("-", "_") + "_byte",
            parse_texish_data_to_byte(exp_name, expline_identifier, expline, flatten_brace_group_to_str(expline))
        )

    elif expline_identifier == "opt-timestamp":
        update_internal_param(
            exp_name, expline_identifier, expline, data_structure,
            "tcp_" + expline_identifier.replace("-", "_") + "_enabled",
            parse_str_boolean(flatten_brace_group_to_str(expline))
        )

    elif expline_identifier == "opt-sack":
        update_internal_param(
            exp_name, expline_identifier, expline, data_structure,
            "tcp_" + expline_identifier.replace("-", "_") + "_enabled",
            parse_str_boolean(flatten_brace_group_to_str(expline))
        )

    elif expline_identifier == "opt-win-scaling":
        update_internal_param(
            exp_name, expline_identifier, expline, data_structure,
            "tcp_" + expline_identifier.replace("-", "_") + "_enabled",
            parse_str_boolean(flatten_brace_group_to_str(expline))
        )

    elif expline_identifier == "opt-pacing":
        update_internal_param(
            exp_name, expline_identifier, expline, data_structure,
            "tcp_" + expline_identifier.replace("-", "_") + "_enabled",
            parse_str_boolean(flatten_brace_group_to_str(expline))
        )

    elif expline_identifier == "no-delay":
        update_internal_param(
            exp_name, expline_identifier, expline, data_structure,
            "tcp_" + expline_identifier.replace("-", "_"),
            parse_str_boolean(flatten_brace_group_to_str(expline))
        )

    elif expline_identifier == "max-seg-lifetime":
        update_internal_param(
            exp_name, expline_identifier, expline, data_structure,
            "tcp_" + expline_identifier.replace("-", "_") + "_ns",
            parse_texish_time_to_ns(exp_name, expline_identifier, expline, flatten_brace_group_to_str(expline))
        )

    elif expline_identifier == "min-rto":
        update_internal_param(
            exp_name, expline_identifier, expline, data_structure,
            "tcp_" + expline_identifier.replace("-", "_") + "_ns",
            parse_texish_time_to_ns(exp_name, expline_identifier, expline, flatten_brace_group_to_str(expline))
        )

    elif expline_identifier == "initial-rtt-estimate":
        update_internal_param(
            exp_name, expline_identifier, expline, data_structure,
            "tcp_" + expline_identifier.replace("-", "_") + "_ns",
            parse_texish_time_to_ns(exp_name, expline_identifier, expline, flatten_brace_group_to_str(expline))
        )

    elif expline_identifier == "connection-timeout":
        update_internal_param(
            exp_name, expline_identifier, expline, data_structure,
            "tcp_" + expline_identifier.replace("-", "_") + "_ns",
            parse_texish_time_to_ns(exp_name, expline_identifier, expline, flatten_brace_group_to_str(expline))
        )

    elif expline_identifier == "delayed-ack-timeout":
        update_internal_param(
            exp_name, expline_identifier, expline, data_structure,
            "tcp_" + expline_identifier.replace("-", "_") + "_ns",
            parse_texish_time_to_ns(exp_name, expline_identifier, expline, flatten_brace_group_to_str(expline))
        )

    elif expline_identifier == "persist-timeout":
        update_internal_param(
            exp_name, expline_identifier, expline, data_structure,
            "tcp_" + expline_identifier.replace("-", "_") + "_ns",
            parse_texish_time_to_ns(exp_name, expline_identifier, expline, flatten_brace_group_to_str(expline))
        )

    else:
        identifier_matched = False
        
    return identifier_matched


# Example:
# The experiment is run for 20~seconds.
def incorporator_experiment_duration(exp_name, expline_identifier, expline, data_structure):
    result = re.match(
        expand_regex_to_be_tolerant_to_whitespace(
            r'[Tt]he experiment is run for ([^\.]*)\.?'
        ),
        flatten_brace_group_to_str(expline)
    )
    if result is not None:
        subgroups = result.groups()
        duration_ns = parse_texish_time_to_ns(exp_name, expline_identifier, expline, subgroups[0])
        if data_structure["duration_ns"][0]:
            raise InterpretExplineError(exp_name, expline_identifier, expline, "Duration is already set")
        data_structure["duration_ns"] = (True, duration_ns)
        return True
    return False


# Example:
# We set a random early detection (RED) queueing discipline with a maximum queue size
# of 100 packets and a binary marking (or drop if the IP packet does not support ECN) threshold at 50 packets.
def incorporator_qdisc_red(exp_name, expline_identifier, expline, data_structure):
    result = re.match(
        expand_regex_to_be_tolerant_to_whitespace(
            r'[Ww]e set a random early detection \(RED\) queueing discipline with a maximum queue '
            r'size of (.*) packets and a binary marking \(or drop if the IP packet does not support '
            r'ECN\) threshold at (.*) packets\.?'
        ),
        flatten_brace_group_to_str(expline)
    )
    if result is not None:
        subgroups = result.groups()
        max_queue_size_pkt = exputil.parse_positive_int(subgroups[0])
        threshold_pkt = exputil.parse_positive_int(subgroups[1])
        if data_structure["link_interface_traffic_control_qdisc"][0]:
            raise InterpretExplineError(exp_name, expline_identifier, expline, "Duration is already set")
        data_structure["link_interface_traffic_control_qdisc"] = (
            True,
            "simple_red(ecn; 1500; 1.0; %d; %d; %dp; 1.0; no_wait; not_gentle)" % (
                threshold_pkt, threshold_pkt, max_queue_size_pkt
            )
        )
        return True
    return False


# Example:
# Every/The link has the following properties: the channel has a delay of 10~$\mu s$, and its link network
# devices have a data rate of 50~Mbit/s, 0.1\% random packet loss, and a FIFO queue of 100 packets.
def incorporator_link_channel_and_network_devices(exp_name, expline_identifier, expline, data_structure):
    result = re.match(
        expand_regex_to_be_tolerant_to_whitespace(
            r'(Every|The) link has the following properties: the channel has a delay of (.*), and '
            r'its network devices have a data rate of (.*), (.*) random packet loss, '
            r'and a FIFO queue of (.*) packets\.?'
        ),
        flatten_brace_group_to_str(expline)
    )
    if result is not None:
        subgroups = result.groups()

        # Link channel delay in ns
        link_channel_delay_ns = parse_texish_time_to_ns(exp_name, expline_identifier, expline, subgroups[1])
        if data_structure["link_channel_delay_ns"][0]:
            raise InterpretExplineError(exp_name, expline_identifier, expline, "Link channel delay is already set")
        data_structure["link_channel_delay_ns"] = (
            True,
            link_channel_delay_ns
        )

        # Data rate in Mb/s
        data_rate_mbps = parse_texish_data_rate_to_megabit_per_s(exp_name, expline_identifier, expline, subgroups[2])
        if data_structure["link_net_device_data_rate_megabit_per_s"][0]:
            raise InterpretExplineError(
                exp_name, expline_identifier, expline, "Link net-device data rate is already set"
            )
        data_structure["link_net_device_data_rate_megabit_per_s"] = (
            True,
            data_rate_mbps
        )

        # Uniform random packet loss percentage
        loss_percentage = parse_texish_percentage(exp_name, expline_identifier, expline, subgroups[3])
        if data_structure["link_net_device_receive_error_model"][0]:
            raise InterpretExplineError(
                exp_name, expline_identifier, expline, "Link net-device receive error model is already set"
            )
        data_structure["link_net_device_receive_error_model"] = (
            True,
            "iid_uniform_random_pkt(%.10f)" % (loss_percentage / 100.0)
        )

        # FIFO queue size in packets
        drop_tail_queue_size_pkt = exputil.parse_positive_int(subgroups[4])
        if data_structure["link_net_device_queue"][0]:
            raise InterpretExplineError(exp_name, expline_identifier, expline, "Link net-device queue is already set")
        data_structure["link_net_device_queue"] = (
            True,
            "drop_tail(%dp)" % drop_tail_queue_size_pkt
        )

        return True
    return False


# Example:
# Delayed acknowledgements are disabled
def incorporator_delayed_ack(exp_name, expline_identifier, expline, data_structure):
    result = re.match(
        expand_regex_to_be_tolerant_to_whitespace(
            r'[Dd]elayed acknowledgements are (enabled|disabled)\.?'
        ),
        flatten_brace_group_to_str(expline)
    )
    if result is not None:
        subgroups = result.groups()
        enabled_or_disabled = parse_str_boolean(subgroups[0])
        if data_structure["tcp_delayed_ack_packet_count"][0]:
            raise InterpretExplineError(exp_name, expline_identifier, expline, "Delayed ACK count is already set")
        if enabled_or_disabled == "true":
            data_structure["tcp_delayed_ack_packet_count"] = (True, 2)
            data_structure["tcp_delayed_ack_timeout_ns"] = (True, 200000000)  # Default 200ms
        else:
            data_structure["tcp_delayed_ack_packet_count"] = (True, 1)
            data_structure["tcp_delayed_ack_timeout_ns"] = (True, 200000000)
        return True
    return False


# Example:
# The send and receive buffer size are set to 1~GB
def incorporator_buffer_size(exp_name, expline_identifier, expline, data_structure):
    result = re.match(
        expand_regex_to_be_tolerant_to_whitespace(
            r'[Tt]he send and receive buffer size are set to ([^\.]*)\.?'
        ),
        flatten_brace_group_to_str(expline)
    )
    if result is not None:
        subgroups = result.groups()
        buffer_size_byte = parse_texish_data_to_byte(exp_name, expline_identifier, expline, subgroups[0])
        if data_structure["tcp_snd_buf_size_byte"][0]:
            raise InterpretExplineError(exp_name, expline_identifier, expline, "Send buffer size is already set")
        if data_structure["tcp_rcv_buf_size_byte"][0]:
            raise InterpretExplineError(exp_name, expline_identifier, expline, "Receive buffer size is already set")
        if buffer_size_byte < 100000:
            raise InterpretExplineError(exp_name, expline_identifier, expline, "Buffer size must be at least 100KB")
        data_structure["tcp_snd_buf_size_byte"] = (True, buffer_size_byte)
        data_structure["tcp_rcv_buf_size_byte"] = (True, buffer_size_byte)
        return True
    return False
