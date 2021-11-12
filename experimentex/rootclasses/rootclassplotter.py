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


class InvalidRunDirError(ValueError):

    def __init__(self, exp_instance_name, run_dir, err_message):
        super().__init__(
            "Instance %s: invalid run dir \"%s\".\nError: %s." % (
                exp_instance_name,
                run_dir,
                err_message
            )
        )


class PlotExpincludeError(ValueError):

    def __init__(self, exp_instance_name, expinclude_filename, err_message):
        super().__init__(
            "Instance %s: expinclude file \"%s\" could not be plotted.\nError: %s." % (
                exp_instance_name,
                expinclude_filename,
                err_message
            )
        )


class RootClassPlotter(ABC):

    def get_root_class_name(self):
        """
        Get the root class name.

        :return: Root class name (must be unique)
        """
        pass

    def plot_for_experiment(
            self,
            exp_instance_name,
            path_to_core,
            list_run_dir_paths_from_core,
            experiment_plots_path_from_core,
            list_expinclude_filenames
    ):
        """
        The goal is to plot all the files in the list, e.g., each being:
        <experiment_plot_path>/<expinclude_filename>

        :param exp_instance_name:       Experiment instance name
                                        (should only be used for info when throwing errors)

        :param path_to_core:            How to get from the current working directory where the Python is being
                                        executed to the core/root path (generally, "..")

        :param list_run_dir_paths_from_core:       List of all run directories belonging to the experiment
                                                   (e.g., [ "temp/runs/<root-class-name>-<exp-hash0>", ... ]

        :param experiment_plots_path_from_core:    How to get from the core/root path to where the experiment
                                                   plots are to be placed (generally, "temp/plots/<exp-name>")

        :param list_expinclude_filenames:         List of expinclude filenames to generate (i.e., plot) in the
                                                  experiment_plots_path_from_core directory.
                                                  (e.g., "x-vs-y.pdf", "metric.txt")

        """
        pass
