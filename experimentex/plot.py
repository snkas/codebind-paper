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
import sys
import copy
import ast
import shutil

from parser import parse
from rootclasses.rootclasses import retrieve_root_class_names_list, get_root_class_plotter


def plot(name_to_child_names, name_to_list_expinclude_filename, clean_slate):

    print("PLOT EXPERIMENTEX EXPINCLUDE FILES")

    # Paths
    runs_path = "../temp/runs"
    plots_path = "../temp/plots"
    path_to_core = ".."
    runs_path_from_core = "temp/runs"
    plots_path_from_core = "temp/plots"

    # Empty the plots directory before starting if asked to
    if clean_slate:
        print("  > Starting with clean slate by removing existing plots directory")
        shutil.rmtree(plots_path)

    # Create the plots directory if it does not exist
    os.makedirs(plots_path, exist_ok=True)

    # Make sure that the experiment instances mapping to run directory names exist
    instance_run_dir_names_mapping_filename = runs_path + "/experiment_instances_to_run_dir_names.txt"
    if not os.path.exists(instance_run_dir_names_mapping_filename):
        raise ValueError(
            "Instance-to-run-dir-names mapping file does not exist: %s\n"
            "Did you run the interpreter beforehand?" % instance_run_dir_names_mapping_filename
        )

    # Read the run directory names for each instance
    with open(instance_run_dir_names_mapping_filename, "r") as f_in:
        experiment_instance_name_to_run_dir_names = ast.literal_eval(f_in.read())
    print("  > Read the experiment-instance-to-run-dir-names mapping")

    # Generate the configurations in a DFS fashion
    for root_class_name in retrieve_root_class_names_list():
        print("  > Plotting instances of root class " + root_class_name)

        # Statistics of the root class
        num_instances = 0
        num_expincludes = 0
        num_actual_plots = 0

        # Retrieve the plotter
        root_class_plotter = get_root_class_plotter(root_class_name)

        # Add all children of the root class at the start
        to_visit = list(copy.deepcopy(name_to_child_names[root_class_name]))
        while len(to_visit) != 0:
            child_name = to_visit.pop(0)

            if len(name_to_child_names[child_name]) == 0:
                # If it does not have children, it must be an instance, as such plots can be made
                num_instances += 1

                if child_name not in experiment_instance_name_to_run_dir_names:
                    print(
                        "WARNING: Experiment instance %s does not have any run directories.\n"
                        "         Did you make any changes in the experiments since the last interpretation?\n"
                        "         To have those changes reflected, please run the interpreter again."
                        % child_name
                    )

                else:

                    # List of all the run directories belonging to this experiment
                    list_run_dir_paths_from_core = []
                    for run_dir_name in experiment_instance_name_to_run_dir_names[child_name]:
                        run_dir_path_from_core = runs_path_from_core + "/" + run_dir_name
                        list_run_dir_paths_from_core.append(run_dir_path_from_core)
                        if not os.path.exists(path_to_core + "/" + run_dir_path_from_core):
                            raise ValueError(
                                "Run directory named \"%s\" does not exist but is listed in the instance mapping"
                                " (Possibly some runs were removed? Running the interpreter should fix this)."
                                % run_dir_name
                            )
                    os.makedirs(plots_path + "/" + child_name, exist_ok=True)

                    # Call the plotter for the list of expinclude filenames to plot
                    list_unique_expinclude_filename = list(sorted(set(name_to_list_expinclude_filename[child_name])))
                    num_expincludes += len(name_to_list_expinclude_filename[child_name])
                    num_actual_plots += len(list_unique_expinclude_filename)
                    root_class_plotter.plot_for_experiment(
                        child_name,
                        path_to_core,
                        list_run_dir_paths_from_core,
                        plots_path_from_core + "/" + child_name,
                        list_unique_expinclude_filename
                    )

            else:
                # If it has children, we go over those
                for v in name_to_child_names[child_name]:
                    to_visit.insert(0, v)  # Child is the parent of its children

        # Print statistics
        print("    >> # of instances............ " + str(num_instances))
        print("    >> # of expincludes.......... " + str(num_expincludes))
        print("    >> # of unique expincludes... " + str(num_actual_plots))

    print("")


def print_usage():
    print("Failed: you must supply one or more TeX files as arguments")
    print("")
    print("Usage: python3 plot.py [--clean-slate] [.tex file] [.tex file] ...")
    print("")
    print("Optional arguments:")
    print("   --clean-slate      Empties the entire plots directory before commencing")
    print("")


def main():
    args = sys.argv[1:]

    # Must have one or more arguments
    if len(args) < 1:
        print_usage()
        exit(1)

    # Optional argument
    clean_slate = (args[0] == "--clean-slate")

    # Cannot be only the optional argument
    if clean_slate and len(args) == 1:
        print_usage()

    else:
        print("")
        args_start_point = 0
        if clean_slate:
            args_start_point = 1
        name_to_child_names, _, name_to_list_expinclude_filename = parse(args[args_start_point:])
        plot(name_to_child_names, name_to_list_expinclude_filename, clean_slate)


if __name__ == "__main__":
    main()
