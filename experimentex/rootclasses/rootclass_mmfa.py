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
import re
import copy
import ast
from hashlib import sha256
import exputil

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


def parse_number_readable(s):
    if s == "none":
        return 0
    elif s == "no":
        return 0
    elif s == "zero":
        return 0
    elif s == "one":
        return 1
    elif s == "two":
        return 2
    elif s == "three":
        return 3
    elif s == "four":
        return 4
    elif s == "five":
        return 5
    elif s == "six":
        return 6
    elif s == "seven":
        return 7
    elif s == "eight":
        return 8
    elif s == "nine":
        return 9
    elif s == "ten":
        return 10
    else:
        return int(s)


def convert_node_letter_to_id(s):
    if s == "A":
        return 0
    elif s == "B":
        return 1
    elif s == "C":
        return 2
    raise ValueError("Invalid node letter (only A, B and C are permitted): " + s)


def convert_node_id_to_letter(i):
    if i == 0:
        return "A"
    elif i == 1:
        return "B"
    elif i == 2:
        return "C"
    raise ValueError("Invalid node id (only 0, 1 and 2 are permitted): " + str(i))


class MmfaRootClassInterpreter(RootClassInterpreter):

    def __init__(self):
        self.root_class_name = "mmfa"

    def get_root_class_name(self):
        return self.root_class_name

    def generate_empty_experiment_data_structure(self):
        return {
            "cap_A_B": (False, None),  # Float or a list of floats to make it multiple values
            "cap_B_C": (False, None),  # Float or a list of floats to make it multiple values
            "num_flows_A_B": (False, None),  # Integer
            "num_flows_B_C": (False, None),  # Integer
            "num_flows_A_C": (False, None),  # Integer
        }

    def interpret_expline_into_experiment_data_structure(self, exp_name, expline_identifier, expline, data_structure):

        # Example:
        # The edge from A to B has a capacity of 3 unit
        result = re.match(
            expand_regex_to_be_tolerant_to_whitespace(
                r'the edge from (.*) to (.*) has a capacity of (.*) unit'
            ),
            flatten_brace_group_to_str(expline)
        )
        if result is not None:
            subgroups = result.groups()
            from_node_id = convert_node_letter_to_id(subgroups[0])
            to_node_id = convert_node_letter_to_id(subgroups[1])
            capacity = exputil.parse_positive_float(subgroups[2])

            if capacity < 0:
                raise InterpretExplineError(exp_name, expline_identifier, expline, "Capacity cannot be negative")

            if from_node_id == 0 and to_node_id == 1:
                if data_structure["cap_A_B"][0]:
                    raise InterpretExplineError(
                        exp_name, expline_identifier, expline, "Capacity between A and B is already set"
                    )
                data_structure["cap_A_B"] = (True, capacity)

            elif from_node_id == 1 and to_node_id == 2:
                if data_structure["cap_B_C"][0]:
                    raise InterpretExplineError(
                        exp_name, expline_identifier, expline, "Capacity between B and C is already set"
                    )
                data_structure["cap_B_C"] = (True, capacity)

            else:
                raise InterpretExplineError(exp_name, expline_identifier, expline, "Link does not exist")

            return data_structure

        ###############################################################

        # Example:
        # We vary the number of flows from A to B between 1 and 4
        result = re.match(
            expand_regex_to_be_tolerant_to_whitespace(
                r'[Ww]e vary the number of flows from (.*) to (.*) between (.*) and (.*)'
            ),
            flatten_brace_group_to_str(expline)
        )
        if result is not None:
            subgroups = result.groups()
            from_node_id = convert_node_letter_to_id(subgroups[0])
            to_node_id = convert_node_letter_to_id(subgroups[1])
            number_low = parse_number_readable(subgroups[2])
            number_high = parse_number_readable(subgroups[3])

            if not(
                    (from_node_id == 0 and to_node_id == 1) or
                    (from_node_id == 1 and to_node_id == 2) or
                    (from_node_id == 0 and to_node_id == 2)
            ):
                raise InterpretExplineError(exp_name, expline_identifier, expline, "Invalid from-to node identifiers")
            if number_low < 0:
                raise InterpretExplineError(exp_name, expline_identifier, expline, "Number cannot be negative")
            if number_low >= number_high:
                raise InterpretExplineError(
                    exp_name, expline_identifier, expline, "Higher number must be higher"
                )
            numbers = []
            for value in range(number_low, number_high + 1, 1):
                numbers.append(value)

            key = "num_flows_%s_%s" % (convert_node_id_to_letter(from_node_id), convert_node_id_to_letter(to_node_id))
            if data_structure[key][0]:
                raise InterpretExplineError(exp_name, expline_identifier, expline, "Number is already set")
            data_structure[key] = (True, numbers)

            return data_structure

        ###############################################################

        # Example:
        # five flows from A to B
        result = re.match(
            expand_regex_to_be_tolerant_to_whitespace(r'([^\s]*) from (.*) to (.*)'),
            flatten_brace_group_to_str(expline)
        )
        result2 = re.match(
            expand_regex_to_be_tolerant_to_whitespace(r'([^\s]*) flow[s]? from (.*) to (.*)'),
            flatten_brace_group_to_str(expline)
        )
        if result2 is not None:
            result = result2
        if result is not None:
            subgroups = result.groups()
            number = parse_number_readable(subgroups[0])
            from_node_id = convert_node_letter_to_id(subgroups[1])
            to_node_id = convert_node_letter_to_id(subgroups[2])

            if not(
                    (from_node_id == 0 and to_node_id == 1) or
                    (from_node_id == 1 and to_node_id == 2) or
                    (from_node_id == 0 and to_node_id == 2)
            ):
                raise InterpretExplineError(exp_name, expline_identifier, expline, "Invalid from-to node identifiers")

            if number < 0:
                raise InterpretExplineError(exp_name, expline_identifier, expline, "Invalid number")

            key = "num_flows_%s_%s" % (convert_node_id_to_letter(from_node_id), convert_node_id_to_letter(to_node_id))
            if data_structure[key][0]:
                raise InterpretExplineError(exp_name, expline_identifier, expline, "Number is already set")
            data_structure[key] = (True, number)

            return data_structure

        # If nothing matched, then it failed
        raise InterpretExplineError(exp_name, expline_identifier, expline, "Did not match any pattern.")

    def generate_run_dirs_for_experiment_data_structure(self, exp_instance_name, runs_path, data_structure):

        # Check validity of data structure
        if not data_structure["cap_A_B"][0]:
            raise RunDirGenerationError(exp_instance_name, "Capacity from A to B is not set")
        if not data_structure["cap_B_C"][0]:
            raise RunDirGenerationError(exp_instance_name, "Capacity from B to C is not set")
        if not data_structure["num_flows_A_B"][0]:
            raise RunDirGenerationError(exp_instance_name, "Number of flows A -> B is not set")
        if not data_structure["num_flows_B_C"][0]:
            raise RunDirGenerationError(exp_instance_name, "Number of flows B -> C is not set")
        if not data_structure["num_flows_A_C"][0]:
            raise RunDirGenerationError(exp_instance_name, "Number of flows A -> C is not set")

        # Cartesian product of the capacity lists
        num_flows_0_1 = []
        if isinstance(data_structure["num_flows_A_B"][1], list):
            num_flows_0_1.extend(data_structure["num_flows_A_B"][1])
        else:
            num_flows_0_1.append(data_structure["num_flows_A_B"][1])
        num_flows_1_2 = []
        if isinstance(data_structure["num_flows_B_C"][1], list):
            num_flows_1_2.extend(data_structure["num_flows_B_C"][1])
        else:
            num_flows_1_2.append(data_structure["num_flows_B_C"][1])
        num_flows_0_2 = []
        if isinstance(data_structure["num_flows_A_C"][1], list):
            num_flows_0_2.extend(data_structure["num_flows_A_C"][1])
        else:
            num_flows_0_2.append(data_structure["num_flows_A_C"][1])
        all_run_data_structures = []
        for val01 in num_flows_0_1:
            for val12 in num_flows_1_2:
                for val02 in num_flows_0_2:
                    new_data_structure = copy.deepcopy(data_structure)
                    new_data_structure["num_flows_A_B"] = True, int(val01)
                    new_data_structure["num_flows_B_C"] = True, int(val12)
                    new_data_structure["num_flows_A_C"] = True, int(val02)
                    all_run_data_structures.append(new_data_structure)

        # Finally, create a run directory for each data structure
        list_run_dir_names = []
        for run_data_structure in all_run_data_structures:

            # Calculate the hash of the data structure
            run_hash = sha256(repr(sorted(run_data_structure.items())).encode('utf-8')).hexdigest()

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
                        raise RunDirGenerationError(
                            exp_instance_name,
                            "Hash matched, but data structure was not equal!"
                        )

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

                # Write the input files
                os.makedirs(run_dir_path + "/input", exist_ok=True)
                with open(run_dir_path + "/input/directed-topology.txt", "w+") as f_topology:
                    f_topology.write("3,2\n")
                    f_topology.write("0,1,%.10f\n" % (run_data_structure["cap_A_B"][1]))
                    f_topology.write("1,2,%.10f\n" % (run_data_structure["cap_B_C"][1]))
                with open(run_dir_path + "/input/flow-paths.txt", "w+") as f_flow_paths:
                    for i in range(run_data_structure["num_flows_A_B"][1]):
                        f_flow_paths.write("0-1\n")
                    for i in range(run_data_structure["num_flows_B_C"][1]):
                        f_flow_paths.write("1-2\n")
                    for i in range(run_data_structure["num_flows_A_C"][1]):
                        f_flow_paths.write("0-1-2\n")

                # Write that it is ready to be run
                with open(run_dir_path + "/input-ready.txt", "w+") as f_out:
                    f_out.write("Yes")

        # Return the list of run directory names
        return list_run_dir_names

    def generate_run_sh_body_for_run_dir(self, relative_runs_path_from_core_path, run_dir_name):
        run_sh_body = ""
        run_sh_body += "\n"
        run_sh_body += "# If the run has already been run before, it can be skipped\n"
        run_sh_body += "if [ -f \"%s/%s/output/finished.txt\" ] && " \
                       "[ $(< \"%s/%s/output/finished.txt\") == \"Yes\" ] ; then\n" \
                       % (
                           relative_runs_path_from_core_path, run_dir_name,
                           relative_runs_path_from_core_path, run_dir_name
                       )
        run_sh_body += "    exit 0\n"
        run_sh_body += "fi\n"
        run_sh_body += "\n"
        run_sh_body += "# Perform the run\n"
        run_sh_body += "cd frameworks/mmfa || exit 1\n"
        run_sh_body += "python3 solve_mmfa.py ../../%s/%s/input ../../%s/%s/output || exit 1\n" % (
            relative_runs_path_from_core_path, run_dir_name,
            relative_runs_path_from_core_path, run_dir_name
        )
        return run_sh_body


class MmfaRootClassPlotter(RootClassPlotter):

    def __init__(self):
        self.root_class_name = "mmfa"

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

        # Check that the run directories are finished
        for run_dir_path_from_core in list_run_dir_paths_from_core:
            run_dir = path_to_core + "/" + run_dir_path_from_core
            if not os.path.exists(run_dir + "/output/finished.txt"):
                raise InvalidRunDirError(exp_instance_name, run_dir, "Run has not been run")
            with open(run_dir + "/output/finished.txt", "r") as f_in:
                if f_in.read().strip() != "Yes":
                    raise InvalidRunDirError(exp_instance_name, run_dir, "Run is not finished")

        # Generate the plots
        for filename_plot in list_expinclude_filenames:

            # Max-flow we just copy the file, however we do remove any unnecessary trailing zeros
            if re.match(r'flow-allocation-([A-C])-([A-C]).txt', filename_plot) is not None:

                # Check from-to
                spl = filename_plot.split("-")
                src_node_id = convert_node_letter_to_id(spl[2])
                dst_node_id = convert_node_letter_to_id(spl[3].split(".")[0])
                if not (
                        (src_node_id == 0 and dst_node_id == 1) or
                        (src_node_id == 1 and dst_node_id == 2) or
                        (src_node_id == 0 and dst_node_id == 2)
                ):
                    raise PlotExpincludeError(
                        exp_instance_name, filename_plot, "Invalid source and/or destination node id"
                    )

                # It must also be a single run directory
                if len(list_run_dir_paths_from_core) != 1:
                    raise PlotExpincludeError(
                        exp_instance_name, filename_plot, "Only possible for an experiment with single run"
                    )
                run_dir = list_run_dir_paths_from_core[0]

                # Read in the flow for each link
                found = -1
                search_for = ""
                if src_node_id == 0 and dst_node_id == 1:
                    search_for = "0-1"
                elif src_node_id == 1 and dst_node_id == 2:
                    search_for = "1-2"
                elif src_node_id == 0 and dst_node_id == 2:
                    search_for = "0-1-2"
                with open("%s/%s/output/flow-allocation.txt" % (path_to_core, run_dir), "r") as f_in:
                    for line in f_in:
                        spl = line.split(",")
                        if spl[1] == search_for:
                            found = float(spl[2])
                with open(path_to_core + "/" + experiment_plots_path_from_core + "/" + filename_plot, "w+") as f_out:
                    f_out.write("%g" % found)

                continue

            # Capacity of one link vs. the maximum flow
            result = re.match(r'num-flows-([A-C])-([A-C])-vs-flow-allocation-([A-C])-([A-C]).pdf', filename_plot)
            if result is not None:

                # Check from-to
                subgroups = result.groups()
                num_flows_from_id = convert_node_letter_to_id(subgroups[0])
                num_flows_to_id = convert_node_letter_to_id(subgroups[1])
                flow_allocation_from_id = convert_node_letter_to_id(subgroups[2])
                flow_allocation_to_id = convert_node_letter_to_id(subgroups[3])

                # Read in the two dimensions we want to plot
                num_flows_and_flow_allocation = []
                for run_dir in list_run_dir_paths_from_core:

                    # Number of flows
                    with open(path_to_core + "/" + run_dir + "/data-structure.txt", "r") as f_in:
                        run_data_structure = ast.literal_eval(f_in.read())
                    num_flows = run_data_structure["num_flows_%s_%s" % (
                        convert_node_id_to_letter(num_flows_from_id),
                        convert_node_id_to_letter(num_flows_to_id)
                    )][1]

                    # Flow allocation
                    search_for = ""
                    if flow_allocation_from_id == 0 and flow_allocation_to_id == 1:
                        search_for = "0-1"
                    elif flow_allocation_from_id == 1 and flow_allocation_to_id == 2:
                        search_for = "1-2"
                    elif flow_allocation_from_id == 0 and flow_allocation_to_id == 2:
                        search_for = "0-1-2"
                    flow_allocation = -1
                    with open(path_to_core + "/" + run_dir + "/output/flow-allocation.txt", "r") as f_in:
                        for line in f_in:
                            spl = line.split(",")
                            if spl[1] == search_for:
                                flow_allocation = float(spl[2])
                                break
                    if flow_allocation == -1:
                        raise PlotExpincludeError(
                            exp_instance_name,
                            filename_plot,
                            "Could not find flow allocation for what we searched for (%s)." % search_for
                        )
                    num_flows_and_flow_allocation.append((num_flows, flow_allocation))

                # Write the data file
                data_filename = "%s/%s/num-flows-%d-%d-vs-flow-allocation-%d-%d.txt" % (
                    path_to_core, experiment_plots_path_from_core, num_flows_from_id, num_flows_to_id,
                    flow_allocation_from_id, flow_allocation_to_id
                )
                with open(data_filename, "w+") as f_out:
                    for num_flows, flow_allocation in sorted(num_flows_and_flow_allocation):
                        f_out.write("%.6f,%.6f\n" % (num_flows, flow_allocation))

                # Finally, we actually want to use gnuplot to accomplish the plotting
                local_shell = exputil.LocalShell()
                pdf_filename = "%s/%s/%s" % (path_to_core, experiment_plots_path_from_core, filename_plot)
                local_shell.copy_file(
                    "%s/experimentex/rootclasses/gnuplot/num-flows-vs-flow-allocation.plt" % path_to_core,
                    "temp.plt"
                )
                local_shell.sed_replace_in_file_plain(
                    "temp.plt",
                    "[X-LABEL]",
                    "Number of flows %s → %s" % (
                        convert_node_id_to_letter(num_flows_from_id),
                        convert_node_id_to_letter(num_flows_to_id)
                    )
                )
                local_shell.sed_replace_in_file_plain(
                    "temp.plt",
                    "[Y-LABEL]",
                    "Alloc. each flow %s → %s" % (
                        convert_node_id_to_letter(flow_allocation_from_id),
                        convert_node_id_to_letter(flow_allocation_to_id)
                    )
                )
                local_shell.sed_replace_in_file_plain("temp.plt", "[OUTPUT-FILE]", pdf_filename)
                local_shell.sed_replace_in_file_plain("temp.plt", "[DATA-FILE]", data_filename)
                local_shell.perfect_exec("gnuplot temp.plt")
                local_shell.remove("temp.plt")

                # Crop the final pdf to make it have less whitespace around it
                local_shell.perfect_exec("pdfcrop " + pdf_filename + " " + pdf_filename)

                continue

            raise PlotExpincludeError(
                exp_instance_name, filename_plot,
                "Cannot plot unknown expinclude filename"
            )
