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

from abc import ABC


class InterpretExplineError(ValueError):

    def __init__(self, exp_name, expline_identifier, expline, err_message):
        super().__init__(
            "%s: expline%s \"%s\" could not be interpreted.\nError: %s." % (
                exp_name,
                "" if expline_identifier == "" else " (id: " + expline_identifier + ")",
                expline,
                err_message
            )
        )


class RunDirGenerationError(ValueError):

    def __init__(self, exp_name, err_message):
        super().__init__(
            "Instance %s: run directory generation failed.\nError: %s." % (
                exp_name,
                err_message
            )
        )


class RootClassInterpreter(ABC):

    def get_root_class_name(self):
        """
        Get the root class name.

        :return: Root class name (must be unique)
        """
        pass

    def generate_empty_experiment_data_structure(self):
        """
        Empty experiment data structure, which later on will be modified when explines are interpreted.
        Be sure that copy.deepcopy() can be called on it to create a deep copy such that
        the hierarchical parsing goes well.

        :return: Experiment data structure (with many placeholders indicating no value yet)
        """
        pass

    def interpret_expline_into_experiment_data_structure(self, exp_name, expline_identifier, expline, data_structure):
        """
        Interpret an expline and modify the experiment data structure accordingly.

        :param exp_name:            Experiment instance/class name (should only be used for info when throwing errors)
        :param expline_identifier:  Expline identifier (optional, can be "")
        :param expline:             Expline text
        :param data_structure:      Experiment data structure (will be updated in-place!)

        :return Updated data structure
        """
        pass

    def generate_run_dirs_for_experiment_data_structure(self, exp_instance_name, runs_path, data_structure):
        """
        Generate all the run directories for a certain experiment data structure.
        If there are no multi-valued properties, it will only be one run directory.
        Else, it should result in a Cartesian product of the multi-valued properties, resulting in many run directories.

        :param exp_instance_name:  Experiment instance name (should only be used for info when throwing errors)
        :param runs_path:          Run directories path from current Python work directory (generally, "../temp/runs")
        :param data_structure:     Experiment data structure

        :return: List of run directory names (e.g., each one being "<root-class-name>-<hash-of-final-data-structure>")
        """
        pass

    def generate_run_sh_body_for_run_dir(self, relative_runs_path_from_core_path, run_dir_name):
        """
        Each run directory will have a bash file called run.sh in it.
        run.sh is supposed to do the following things:
        - Start (already done): cd to the core path
        - You must supply the body:
            * If the run has already been executed (e.g., due to the presence of a file indicating
              a successful run, like finished.txt or so), it should just exit 0.
            * Else, execute the run. Exit 0 if successful, exit 1 if failed.

        :param relative_runs_path_from_core_path:  Run directories path (generally, "temp/runs")
        :param run_dir_name:                       Run directory name

        :return: run.sh body
        """
        pass
