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
import math


# Import the abstract class for interpreter
from ..rootclassinterpreter import (
    InterpretExplineError,
)


def parse_texish_time_to_ns(exp_name, expline_identifier, expline, texish_str):
    texish_str = texish_str.strip()

    # Format expected: [quantity]~[unit]
    split_by_tilde = texish_str.split("~", 2)
    if len(split_by_tilde) != 2:
        raise InterpretExplineError(
            exp_name, expline_identifier, expline,
            "TeX-ish time should be of format \"[quantity]~[unit]\" (e.g., \"4.3~s\"). "
            "Invalid: " + texish_str
        )
    quantity = exputil.parse_positive_float(split_by_tilde[0])
    unit = split_by_tilde[1]
    if unit == "s" or unit == "seconds":  # Seconds
        return int(math.floor(quantity * 1000000000.0))
    elif unit == "ms" or unit == "milliseconds":  # Milliseconds
        return int(math.floor(quantity * 1000000.0))
    elif unit == "$\\mu s$" or unit == "microseconds":  # Microseconds
        return int(math.floor(quantity * 1000.0))
    elif unit == "ns" or unit == "nanoseconds":  # Nanoseconds
        return int(math.floor(quantity))
    else:
        raise InterpretExplineError(exp_name, expline_identifier, expline, "Unknown time unit: " + unit)


def parse_texish_data_rate_to_megabit_per_s(exp_name, expline_identifier, expline, texish_str):
    texish_str = texish_str.strip()

    # Format expected: [quantity]~[unit]
    split_by_tilde = texish_str.split("~", 2)
    if len(split_by_tilde) != 2:
        raise InterpretExplineError(
            exp_name, expline_identifier, expline,
            "TeX-ish data rate should be of format \"[quantity]~[unit]\" (e.g., \"4.6~Gbit/s\"). "
            "Invalid: " + texish_str
        )
    quantity = exputil.parse_positive_float(split_by_tilde[0])
    unit = split_by_tilde[1]
    if unit == "bit/s" or unit == "bps":  # Mbit/s
        return quantity / 1000000.0
    elif unit == "Kbit/s" or unit == "Kbps":  # Kbit/s
        return quantity / 1000.0
    elif unit == "Mbit/s" or unit == "Mbps":  # Mbit/s
        return quantity
    elif unit == "Gbit/s" or unit == "Gbps":  # Gbit/s
        return quantity * 1000.0
    else:
        raise InterpretExplineError(exp_name, expline_identifier, expline, "Unknown data rate unit: " + unit)


def parse_texish_data_to_byte(exp_name, expline_identifier, expline, texish_str):
    texish_str = texish_str.strip()

    # Format expected: [quantity]~[unit]
    split_by_tilde = texish_str.split("~", 2)
    if len(split_by_tilde) != 2:
        raise InterpretExplineError(
            exp_name, expline_identifier, expline,
            "TeX-ish data should be of format \"[quantity]~[byte-unit]\" (e.g., \"4.6~MB\"). "
            "Invalid: " + texish_str
        )
    quantity = exputil.parse_positive_float(split_by_tilde[0])
    unit = split_by_tilde[1]
    if unit == "B" or unit == "byte":  # B
        return quantity
    elif unit == "KB" or unit == "kilobyte":  # KB
        return int(math.floor(quantity * 1000.0))
    elif unit == "MB" or unit == "megabyte":  # MB
        return int(math.floor(quantity * 1000000.0))
    elif unit == "GB" or unit == "gigabyte":  # GB
        return int(math.floor(quantity * 1000000000.0))
    else:
        raise InterpretExplineError(exp_name, expline_identifier, expline, "Unknown unit: " + unit)


def parse_texish_percentage(exp_name, expline_identifier, expline, texish_str):
    texish_str = texish_str.strip()

    # Format expected: [quantity]\%
    if not texish_str.endswith("\\%"):
        raise InterpretExplineError(
            exp_name, expline_identifier, expline,
            "TeX-ish percentage should be of format \"[percentage]%\" (e.g., \"5.89%\"). "
            "Invalid: " + texish_str
        )
    return exputil.parse_positive_float(texish_str[:-2])


def parse_texish_int_percentage(exp_name, expline_identifier, expline, texish_str):
    texish_str = texish_str.strip()

    # Format expected: [quantity]\%
    if not texish_str.endswith("\\%"):
        raise InterpretExplineError(
            exp_name, expline_identifier, expline,
            "TeX-ish integer percentage should be of format \"[percentage]%\" (e.g., \"33%\"). "
            "Invalid: " + texish_str
        )
    return exputil.parse_positive_int(texish_str[:-2])


def parse_congestion_protocol(exp_name, expline_identifier, expline, flattened_str):
    flattened_str = flattened_str.strip()

    # Format expected: direct text matching
    if flattened_str == "TCP NewReno":
        return "TcpNewReno"
    elif flattened_str == "TCP Cubic":
        return "TcpCubic"
    elif flattened_str == "TCP Vegas":
        return "TcpVegas"
    elif flattened_str == "DCTCP":
        return "TcpDctcp"
    else:
        raise InterpretExplineError(exp_name, expline_identifier, expline, "Unknown protocol")
