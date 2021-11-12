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
import shutil

from parser import parse
from rootclasses.rootclasses import retrieve_root_class_names_list, get_root_class_interpreter


def interpret(name_to_child_names, name_to_list_identifier_with_expline, clean_slate, remove_unused):

    print("INTERPRET EXPERIMENTEX TO RUNS")

    # Runs directory
    runs_path = "../temp/runs"
    relative_runs_path_from_core_path = "temp/runs"

    # Empty the runs directory before starting if asked to
    if clean_slate:
        print("  > Starting with clean slate by removing existing runs directory")
        shutil.rmtree(runs_path)

    # Create the runs directory if it does not exist
    os.makedirs(runs_path, exist_ok=True)

    # All configurations
    run_dir_names_set = set()
    experiment_instance_name_to_run_dir_names = {}

    # Generate the configurations in a DFS fashion
    for root_class_name in retrieve_root_class_names_list():
        print("  > Interpreting instances of root class " + root_class_name)

        # Statistics of the root class
        num_instances = 0
        num_run_dirs = 0
        num_run_dir_names_at_start = len(run_dir_names_set)

        # Retrieve the interpreter
        root_class_interpreter = get_root_class_interpreter(root_class_name)

        # It all starts at the root
        name_to_data_structure = {
            root_class_name: root_class_interpreter.generate_empty_experiment_data_structure()
        }

        # Add all children of the root class at the start
        to_visit = list(map(
            lambda x: (x, root_class_name),
            copy.deepcopy(name_to_child_names[root_class_name])
        ))

        while len(to_visit) != 0:
            child_name, parent_name = to_visit.pop(0)

            # The child becomes a copy of its parent
            name_to_data_structure[child_name] = copy.deepcopy(name_to_data_structure[parent_name])

            # ... with the additional explines added to it
            for identifier_opt, expline in name_to_list_identifier_with_expline[child_name]:
                name_to_data_structure[child_name] = \
                    root_class_interpreter.interpret_expline_into_experiment_data_structure(
                        child_name,
                        identifier_opt,
                        expline,
                        name_to_data_structure[child_name]
                    )

            if len(name_to_child_names[child_name]) == 0:
                # If it does not have children, it must be an instance,
                # as such the run directories must be generated

                # Generate all the run directories for the experiment instance
                num_instances += 1
                run_dir_names = root_class_interpreter.generate_run_dirs_for_experiment_data_structure(
                    child_name,
                    runs_path,
                    name_to_data_structure[child_name]
                )
                experiment_instance_name_to_run_dir_names[child_name] = run_dir_names

                # Generate run.sh for each run directory
                for run_dir_name in run_dir_names:
                    run_dir_names_set.add(run_dir_name)
                    num_run_dirs += 1
                    with open(runs_path + "/" + run_dir_name + "/run.sh", "w+") as f_out:
                        f_out.write("#!/bin/bash\n")
                        f_out.write("\n")
                        f_out.write("# " + child_name + " :: " + run_dir_name + "\n")
                        f_out.write("\n")
                        f_out.write("# Navigate to core path\n")
                        f_out.write("cd ../../.. || exit 1\n")
                        f_out.write("\n")
                        f_out.write("# Body\n")
                        f_out.write(root_class_interpreter.generate_run_sh_body_for_run_dir(
                            relative_runs_path_from_core_path,
                            run_dir_name
                        ))
                        f_out.write("\n")
            else:
                # If it has children, then we are not yet done (must be a class)
                for v in name_to_child_names[child_name]:
                    to_visit.insert(0, (v, child_name))  # Child is the parent of its children

        # Print statistics
        print("    >> # of instances......... " + str(num_instances))
        print("    >> # of run directories... " + str(num_run_dirs))
        print("       ... of which unique: " + str(len(run_dir_names_set) - num_run_dir_names_at_start))

    # Remove unused run directories
    if remove_unused:
        print("  > Removing unused run directories...")
        num_removed = 0
        for item in os.listdir(runs_path):
            if os.path.isdir(runs_path + "/" + item):
                if item not in run_dir_names_set:
                    shutil.rmtree(runs_path + "/" + item)
                    num_removed += 1
        print("    >> Total removed... " + str(num_removed))

    # Print the mapping of experiment instance to run directory names
    with open(runs_path + "/experiment_instances_to_run_dir_names.txt", "w+") as f_out:
        f_out.write(str(experiment_instance_name_to_run_dir_names))
    print("  > Wrote the experiment-instance-to-run-dir-names mapping")

    print("")


def print_usage():
    print("Failed: you must supply one or more TeX files as arguments")
    print("")
    print("Usage: python3 interpret.py [--clean OR --remove-unused] [.tex file] [.tex file] ...")
    print("")
    print("Optional arguments (mutually exclusive):")
    print("   --clean-slate      Empties the entire runs directory before commencing")
    print("   --remove-unused    Removes any run directories which were not generated by this interpret call")
    print("")


def main():
    args = sys.argv[1:]

    # Must have one or more arguments
    if len(args) < 1:
        print_usage()
        exit(1)

    # Optional arguments
    clean_slate = args[0] == "--clean-slate"
    remove_unused = args[0] == "--remove-unused"

    if len(args) == 1 and (clean_slate or remove_unused):
        print_usage()

    else:
        print("")
        args_start_point = 0
        if clean_slate or remove_unused:
            args_start_point = 1
        name_to_child_names, name_to_list_identifier_with_expline, _ = parse(args[args_start_point:])
        interpret(name_to_child_names, name_to_list_identifier_with_expline, clean_slate, remove_unused)


if __name__ == "__main__":
    main()
