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

# Import the abstract class for interpreter
from .rootclassinterpreter import (
    RootClassInterpreter
)

# Import the abstract class for plotter
from .rootclassplotter import (
    RootClassPlotter,
    PlotExpincludeError
)


class TopListsRootClassInterpreter(RootClassInterpreter):

    def __init__(self):
        self.root_class_name = "top-lists"

    def get_root_class_name(self):
        return self.root_class_name

    def generate_empty_experiment_data_structure(self):
        return {}

    def incorporate_expline_into_experiment_data_structure(self, exp_name, expline_identifier, expline, data_structure):
        raise ValueError("No explines are permitted for top-lists")

    def generate_run_dirs_for_experiment_data_structure(self, exp_instance_name, runs_path, data_structure):
        return []

    def generate_run_sh_body_for_run_dir(self, relative_runs_path_from_core_path, run_dir_name):
        run_sh_body = "exit 0\n"
        return run_sh_body


class TopListsRootClassPlotter(RootClassPlotter):

    def __init__(self):
        self.root_class_name = "top-lists"

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

        # Generate the plots
        for filename_plot in list_expinclude_filenames:

            # All plots have actually already been prepared during the building of the framework
            # For running more metrics, see frameworks/top-lists/generate_data.py
            # (this was done because it takes quite some time to process the data)
            if filename_plot == "plot-original-2c.pdf":
                local_shell = exputil.LocalShell()
                local_shell.copy_file(
                    "%s/frameworks/top-lists/pdf/plot_original_2c.pdf" % path_to_core,
                    "%s/%s/%s" % (path_to_core, experiment_plots_path_from_core, filename_plot)
                )

                # Crop the final pdf to make it have less whitespace around it
                pdf_filename = path_to_core + "/" + experiment_plots_path_from_core + "/" + filename_plot
                local_shell.perfect_exec("pdfcrop " + pdf_filename + " " + pdf_filename)

                continue

            result = re.match(r'plot-rank-against-daily-change-(.*)\.pdf', filename_plot)  # ([^\.]*)
            if result is not None:
                subgroups = result.groups()
                statistic = subgroups[0].replace("-", "_")

                # Statistic name
                if statistic == "mean":
                    statistic_y_label = "Mean daily change"
                elif statistic == "median":
                    statistic_y_label = "Median daily change"
                elif statistic == "min":
                    statistic_y_label = "Minimum daily change"
                elif statistic == "max":
                    statistic_y_label = "Maximum daily change"
                elif statistic.startswith("percentile_"):  # E.g., percentile_44
                    statistic_y_label = "%gth %%-tile daily change" \
                                        % exputil.parse_positive_int(statistic.split("_")[1])
                else:
                    raise ValueError("Invalid statistic: " + statistic)

                # Data files
                data_dir = path_to_core + "/frameworks/top-lists/data"
                data_filename_alexa_old = data_dir + "/alexa_old_rank_against_" + statistic + ".csv"
                data_filename_alexa_new = data_dir + "/alexa_new_rank_against_" + statistic + ".csv"
                data_filename_majestic_joint = data_dir + "/majestic_joint_rank_against_" + statistic + ".csv"
                data_filename_umbrella_joint = data_dir + "/umbrella_joint_rank_against_" + statistic + ".csv"

                # Gnuplot
                local_shell = exputil.LocalShell()
                pdf_filename = (
                        path_to_core + "/" + experiment_plots_path_from_core
                        + "/" + filename_plot
                )
                local_shell.copy_file(
                    path_to_core + "/experimentex/rootclasses/gnuplot/plot-rank-against-daily-change-statistic.plt",
                    "temp.plt"
                )
                local_shell.sed_replace_in_file_plain("temp.plt", "[STATISTIC-Y-LABEL]", statistic_y_label)
                local_shell.sed_replace_in_file_plain("temp.plt", "[OUTPUT-FILE]", pdf_filename)
                local_shell.sed_replace_in_file_plain("temp.plt", "[DATA-FILE-ALEXA-OLD]", data_filename_alexa_old)
                local_shell.sed_replace_in_file_plain("temp.plt", "[DATA-FILE-ALEXA-NEW]", data_filename_alexa_new)
                local_shell.sed_replace_in_file_plain(
                    "temp.plt", "[DATA-FILE-MAJESTIC-JOINT]", data_filename_majestic_joint
                )
                local_shell.sed_replace_in_file_plain(
                    "temp.plt", "[DATA-FILE-UMBRELLA-JOINT]", data_filename_umbrella_joint
                )
                local_shell.perfect_exec("gnuplot temp.plt")
                local_shell.remove("temp.plt")

                # Crop the final pdf to make it have less whitespace around it
                local_shell.perfect_exec("pdfcrop " + pdf_filename + " " + pdf_filename)

                continue

            result = re.match(
                r'(alexa-18|alexa-1318|umbrella-joint|majestic-joint)-daily-change-rank-([0-9]+)-(.*)\.txt',
                filename_plot
            )
            if result is not None:
                subgroups = result.groups()
                top_list_name = subgroups[0]
                rank = subgroups[1]
                statistic = subgroups[2].replace("-", "_")

                # For the file, find the correct naming
                if top_list_name == "alexa-18":
                    top_list_id_name = "alexa_new"
                elif top_list_name == "alexa-1318":
                    top_list_id_name = "alexa_old"
                elif top_list_name == "umbrella-joint":
                    top_list_id_name = "umbrella_joint"
                elif top_list_name == "majestic-joint":
                    top_list_id_name = "majestic_joint"
                else:
                    raise PlotExpincludeError(
                        exp_instance_name, filename_plot, "Unknown top list id name: " + top_list_name
                    )

                # Read in data
                columns = exputil.read_csv_direct_in_columns(
                    "%s/frameworks/top-lists/data/%s_rank_against_%s.csv"
                    % (path_to_core, top_list_id_name, statistic),
                    "pos_int,pos_float"
                )
                rank_list = columns[0]
                metric_value_list = columns[1]
                found = False
                found_metric_value = -1
                for i in range(len(rank_list)):
                    if rank_list[i] == int(rank):
                        found = True
                        found_metric_value = metric_value_list[i]
                        break
                if not found:
                    raise PlotExpincludeError(
                        exp_instance_name, filename_plot, "Unknown rank: " + rank
                    )

                # Write final file
                with open("%s/%s/%s" % (path_to_core, experiment_plots_path_from_core, filename_plot), "w+") as f_out:
                    f_out.write("%.1f\\%%" % found_metric_value)

                continue

            # If nothing matched, throw error
            raise PlotExpincludeError(exp_instance_name, filename_plot, "Unknown plot filename")
