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
import copy
from TexSoup import TexSoup as TexSoup
from TexSoup.data import TexNode, TexCmd, BraceGroup, BracketGroup
from TexSoup.utils import Token

from rootclasses.rootclasses import retrieve_root_class_names_list


# All valid ExperimenTeX commands
EXPERIMENTEX_COMMANDS = [
    "expclass",             # \expclass{name-sub}{name-super}
    "expinstance",          # \expinstance{name-inst}{name-super}
    "expline",              # \expline[identifier (opt)]{name}{expline}
    "expincludetext",       # \expincludetext{name-inst}{output.ext}
    "expincludegraphics",   # \expincludegraphics[...]{name-inst}{output.ext}
]


class ExperimenTeXError(ValueError):

    def __init__(self, message):
        super().__init__(message)


class TraceableExperimenTeXError(ValueError):

    def __init__(self, tex_filename, offending_tex_node, message):
        super().__init__(
            "\nTeX file........ %s\nError........... %s\nOffending TeX... %s" % (
                tex_filename,
                message,
                str(offending_tex_node)
            )
        )


def parse_tex_file(experimentex_commands_list, tex_filename):
    """
    Parses a TeX file searching for the ExperimenTeX commands.

    :param experimentex_commands_list: List of ExperimenTeX commands already found by parsing previous TeX files
    :param tex_filename: Tex source filename

    :return: Updated list of ExperimenTeX commands. Each entry is a dictionary of tex_filename, tex_node, tex_command,
             and the other command-specific arguments
    """
    start_num = len(experimentex_commands_list)

    # File must exist
    if not os.path.isfile(tex_filename):
        raise FileNotFoundError("Input TeX filename does not exist: " + tex_filename)

    # Parse TeX
    tex_file = open(tex_filename, "r")
    soup = TexSoup(tex_file)
    tex_file.close()

    # Loop through it in a depth-first search of the children (= only the TexNode's)
    # Other options: contents = both TexNode's and Token's
    # In TexSoup, there are TexNode's and Token's.
    # TexNode's have a TeX expression in them. Token's are text.
    to_visit = list(soup.children)
    while len(to_visit) != 0:
        item = to_visit.pop(0)
        if type(item) == TexNode and type(item.expr) == TexCmd and item.name in EXPERIMENTEX_COMMANDS:

            # Format: \expline{name}{expline}
            if item.name == "expline":

                if len(item.args) != 2 and len(item.args) != 3:
                    raise TraceableExperimenTeXError(
                        tex_filename,
                        item,
                        "\\expline[identifier (opt)]{name-inst}{output.ext} must have two brace group arguments"
                    )

                # Handle if there is an optional bracket group first
                identifier_opt = ""
                name_inst_or_class = item.args[0]
                expline = item.args[1]
                if len(item.args) == 3:
                    identifier_opt = item.args[0]
                    name_inst_or_class = item.args[1]
                    expline = item.args[2]
                    if type(identifier_opt) != BracketGroup:
                        raise TraceableExperimenTeXError(
                            tex_filename,
                            item,
                            "\\expline[identifier (opt)]{name-inst}{output.ext} "
                            "optional argument is not a bracket group"
                        )

                    # Optional bracket group is identifier
                    if type(identifier_opt.contents[0]) != Token or len(identifier_opt.contents) != 1:
                        raise TraceableExperimenTeXError(
                            tex_filename,
                            item,
                            "\\expline[identifier (opt)]{name}{expline} optional bracket group "
                            "must contain a single expline identifier string."
                        )
                    identifier_opt = str(identifier_opt.contents[0]).strip()

                # First brace group is name (instance or class)
                if type(name_inst_or_class) != BraceGroup:
                    raise TraceableExperimenTeXError(
                        tex_filename,
                        item,
                        "\\expline[identifier (opt)]{name}{expline} first argument is not a brace group"
                    )
                if type(name_inst_or_class.contents[0]) != Token or len(name_inst_or_class.contents) != 1:
                    raise TraceableExperimenTeXError(
                        tex_filename,
                        item,
                        "\\expline[identifier (opt)]{name}{expline} first argument brace group "
                        "must contain a single experiment name string."
                    )
                name_inst_or_class = str(name_inst_or_class.contents[0]).strip()

                # Second brace group is expline
                if type(expline) != BraceGroup:
                    raise TraceableExperimenTeXError(
                        tex_filename,
                        item,
                        "\\expline[identifier (opt)]{name}{expline} second argument is not a brace group"
                    )

                # Add to expressions
                experimentex_commands_list.append(
                    {
                        "tex_filename": tex_filename,
                        "tex_node": item,
                        "tex_command": item.name,
                        "identifier_opt": identifier_opt,
                        "name_inst_or_class": name_inst_or_class,
                        "expline": expline
                    }
                )

            elif item.name == "expclass":   # Format: \expclass{name-sub}{name-super}

                if len(item.args) != 2:
                    raise TraceableExperimenTeXError(
                        tex_filename,
                        item,
                        "\\expclass{name-sub}{name-super} must have two brace group arguments"
                    )

                # First brace group is subclass experiment name
                name_subclass = item.args[0]
                if type(name_subclass) != BraceGroup:
                    raise TraceableExperimenTeXError(
                        tex_filename,
                        item,
                        "\\expclass{name-sub}{name-super} first argument is not a brace group"
                    )
                if type(name_subclass.contents[0]) != Token or len(name_subclass.contents) != 1:
                    raise TraceableExperimenTeXError(
                        tex_filename,
                        item,
                        "\\expclass{name-sub}{name-super} first argument brace group "
                        "must contain a single experiment class name string"
                    )
                parsed_name_subclass = str(name_subclass.contents[0]).strip()

                # Second brace group is superclass experiment name
                name_superclass = item.args[1]
                if type(name_superclass) != BraceGroup:
                    raise TraceableExperimenTeXError(
                        tex_filename,
                        item,
                        "\\expclass{name-sub}{name-super} second argument is not a brace group"
                    )
                if type(name_superclass.contents[0]) != Token or len(name_superclass.contents) != 1:
                    raise TraceableExperimenTeXError(
                        tex_filename,
                        item,
                        "\\expclass{name-sub}{name-super} second argument brace group "
                        "must contain a single experiment class name string"
                    )
                parsed_name_superclass = str(name_superclass.contents[0]).strip()

                # Add to expressions
                experimentex_commands_list.append(
                    {
                        "tex_filename": tex_filename,
                        "tex_node": item,
                        "tex_command": item.name,
                        "name_subclass": parsed_name_subclass,
                        "name_superclass": parsed_name_superclass,
                    }
                )

            elif item.name == "expinstance":   # Format: \expinstance{name-inst}{name-super}

                if len(item.args) != 2:
                    raise TraceableExperimenTeXError(
                        tex_filename,
                        item,
                        "\\expinstance{name-inst}{name-super} must have two brace group arguments"
                    )

                # First brace group is instance name
                parsed_inst_name = item.args[0]
                if type(parsed_inst_name) != BraceGroup:
                    raise TraceableExperimenTeXError(
                        tex_filename,
                        item,
                        "\\expinstance{name-inst}{name-super} first argument is not a brace group"
                    )
                if type(parsed_inst_name.contents[0]) != Token or len(parsed_inst_name.contents) != 1:
                    raise TraceableExperimenTeXError(
                        tex_filename,
                        item,
                        "\\expinstance{name-inst}{name-super} first argument brace group "
                        "must contain a single instance name string"
                    )
                parsed_inst_name = str(parsed_inst_name.contents[0]).strip()

                # Second brace group is superclass experiment name
                superclass_exp_name = item.args[1]
                if type(superclass_exp_name) != BraceGroup:
                    raise TraceableExperimenTeXError(
                        tex_filename,
                        item,
                        "\\expinstance{name-inst}{name-super} second argument is not a brace group"
                    )
                if type(superclass_exp_name.contents[0]) != Token or len(superclass_exp_name.contents) != 1:
                    raise TraceableExperimenTeXError(
                        tex_filename,
                        item,
                        "\\expinstance{name-inst}{name-super} second argument brace group "
                        "must contain a single experiment class name string"
                    )
                parsed_superclass_name = str(superclass_exp_name.contents[0]).strip()

                # Add to expressions
                experimentex_commands_list.append(
                    {
                        "tex_filename": tex_filename,
                        "tex_node": item,
                        "tex_command": item.name,
                        "name_inst": parsed_inst_name,
                        "name_superclass": parsed_superclass_name,
                    }
                )

            elif item.name == "expincludegraphics":

                if len(item.args) != 2 and len(item.args) != 3:
                    raise TraceableExperimenTeXError(
                        tex_filename,
                        item,
                        "\\%s[...]{name-inst}{output.ext} must have two brace group arguments" % item.name
                    )

                # Handle if there is an optional bracket group first
                name_inst = item.args[0]
                expinclude_filename = item.args[1]
                if len(item.args) == 3:
                    name_inst = item.args[1]
                    expinclude_filename = item.args[2]
                    if type(item.args[0]) != BracketGroup:
                        raise TraceableExperimenTeXError(
                            tex_filename,
                            item,
                            "\\%s[...]{name-inst}{output.ext} optional argument is not a bracket group"
                            % item.name
                        )

                # First brace group is experiment name
                if type(name_inst) != BraceGroup:
                    raise TraceableExperimenTeXError(
                        tex_filename,
                        item,
                        "\\%s[...]{name-inst}{output.ext} first argument is not a brace group" % item.name
                    )
                if type(name_inst.contents[0]) != Token or len(name_inst.contents) != 1:
                    raise TraceableExperimenTeXError(
                        tex_filename,
                        item,
                        "\\%s[...]{name-inst}{output.ext} first argument brace group "
                        "must contain a single experiment name string." % item.name
                    )
                name_inst = str(name_inst.contents[0]).strip()

                # Second brace group is the output.ext
                if type(expinclude_filename) != BraceGroup:
                    raise TraceableExperimenTeXError(
                        tex_filename,
                        item,
                        "\\%s[...]{name-inst}{output.ext} second argument is not a brace group" % item.name
                    )
                if type(expinclude_filename.contents[0]) != Token or len(expinclude_filename.contents) != 1:
                    raise TraceableExperimenTeXError(
                        tex_filename,
                        item,
                        "\\%s[...]{name-inst}{output.ext} second argument brace group "
                        "must contain a single output.ext string." % item.name
                    )
                expinclude_filename = str(expinclude_filename.contents[0]).strip()

                # Add to expressions
                experimentex_commands_list.append(
                    {
                        "tex_filename": tex_filename,
                        "tex_node": item,
                        "tex_command": item.name,
                        "name_inst": name_inst,
                        "expinclude_filename": expinclude_filename,
                    }
                )

            elif item.name == "expincludetext":

                if len(item.args) != 2:
                    raise TraceableExperimenTeXError(
                        tex_filename,
                        item,
                        "\\%s{name-inst}{output.ext} must have two brace group arguments" % item.name
                    )

                # First brace group is instance name
                name_inst = item.args[0]
                if type(name_inst) != BraceGroup:
                    raise TraceableExperimenTeXError(
                        tex_filename,
                        item,
                        "\\%s{name-inst}{output.ext} first argument is not a brace group" % item.name
                    )
                if type(name_inst.contents[0]) != Token or len(name_inst.contents) != 1:
                    raise TraceableExperimenTeXError(
                        tex_filename,
                        item,
                        "\\%s{name-inst}{output.ext} first argument brace group "
                        "must contain a single instance name string." % item.name
                    )
                name_inst = str(name_inst.contents[0]).strip()

                # Second brace group is the output.ext
                expinclude_filename = item.args[1]
                if type(expinclude_filename) != BraceGroup:
                    raise TraceableExperimenTeXError(
                        tex_filename,
                        item,
                        "\\%s{name-inst}{output.ext} second argument is not a brace group" % item.name
                    )
                if len(expinclude_filename.contents) != 1 or type(expinclude_filename.contents[0]) != Token:
                    raise TraceableExperimenTeXError(
                        tex_filename,
                        item,
                        "\\%s{name-inst}{output.ext} second argument brace group "
                        "must contain a single output.ext string." % item.name
                    )
                expinclude_filename = str(expinclude_filename.contents[0]).strip()

                # Add to expressions
                experimentex_commands_list.append(
                    {
                        "tex_filename": tex_filename,
                        "tex_node": item,
                        "tex_command": item.name,
                        "name_inst": name_inst,
                        "expinclude_filename": expinclude_filename,
                    }
                )

            else:
                raise ValueError("Unknown interesting TeX node name: " + item.name)

        else:
            for u in reversed(list(item.children)):
                to_visit.insert(0, u)

    # Result
    print("  > %s contained %d ExperimenTeX commands" % (tex_filename, len(experimentex_commands_list) - start_num))

    # Return all interesting TeX nodes
    return experimentex_commands_list


def parse_tex_files(tex_filenames):
    """
    Parse all TeX files and return the experiments

    :param tex_filenames: List of TeX filenames (order is important)

    :return: List of ExperimenTeX commands
    """
    print("PARSING EXPERIMENTEX")
    print("  > %d file%s to parse" % (len(tex_filenames), "s" if len(tex_filenames) > 1 else ""))

    # Go over each TeX file
    experimentex_commands_list = []
    for filename in tex_filenames:
        experimentex_commands_list = parse_tex_file(experimentex_commands_list, filename)

    print("  > Total: %d ExperimenTeX commands" % len(experimentex_commands_list))
    print("")
    return experimentex_commands_list


def process_inheritance(experimentex_commands_list):
    """
    Take in all the ExperimenTeX commands and generates
    a representation used to call interpreters and plotters.

    :param experimentex_commands_list: List of parsed ExperimenTeX commands

    :return: 3-tuple of (
                name_to_child_names,                       (which encodes the inheritance)
                name_to_list_identifier_with_expline,      (which encodes for each name its list of explines)
                name_to_output_plot_filenames              (which encodes for each name its list of expinclude 
                                                            filenames)
             )
             ... when these are combined with the root class name list from retrieve_root_class_names_list(),
             all information within the TeX is accessible.
    """

    # Header
    print("PROCESSING TEX-ENFORCED INHERITANCE")

    # Each of the four names categories is distinct
    root_class_names_list = retrieve_root_class_names_list()
    root_class_names_set = set(copy.deepcopy(root_class_names_list))
    tex_parsed_class_names = set()
    instance_names = set()
    all_names_list = copy.deepcopy(root_class_names_list)  # Combination of all four name in an ordered list
    all_names_set = set(copy.deepcopy(all_names_list))  # Combination of all five name sets

    # Mapping of experiment name (class or instance) to list of explines
    name_to_list_identifier_with_expline = {}
    name_to_list_expinclude_filename = {}
    name_to_parent_class_name = {}
    tex_parsed_class_names_which_have_been_extended = set()

    # Known children of a name:
    # Root classes must have 0+
    # TeX parsed classes must have 1+
    # Instances must have 0
    name_to_child_names = {}
    for name in root_class_names_list:
        name_to_child_names[name] = []
        name_to_list_identifier_with_expline[name] = []

    # Go over each ExperimenTeX command
    for tex_command in experimentex_commands_list:

        # Explines
        if tex_command["tex_command"] == "expline":
            name_inst_or_class = tex_command["name_inst_or_class"]

            # It cannot be a root class
            if name_inst_or_class in root_class_names_set:
                raise TraceableExperimenTeXError(
                    tex_command["tex_filename"],
                    tex_command["tex_node"],
                    "You cannot add an expline to a root class: %s" % name_inst_or_class
                )
            
            # It also cannot be a class which has already been extended from
            elif name_inst_or_class in tex_parsed_class_names_which_have_been_extended:
                raise TraceableExperimenTeXError(
                    tex_command["tex_filename"],
                    tex_command["tex_node"],
                    "Cannot add another expline to a class which has already been extended earlier: %s"
                    % name_inst_or_class
                )
            
            # It must be either be for an instance or class
            elif name_inst_or_class not in instance_names and name_inst_or_class not in tex_parsed_class_names:
                raise TraceableExperimenTeXError(
                    tex_command["tex_filename"],
                    tex_command["tex_node"],
                    "Undefined name: %s. You must call \\expinstance or \\expclass beforehand to declare it." 
                    % name_inst_or_class
                )

            # Add expline to the explines list
            name_to_list_identifier_with_expline[name_inst_or_class].append(
                (tex_command["identifier_opt"], tex_command["expline"])
            )

        elif tex_command["tex_command"] == "expclass":
            name_subclass = tex_command["name_subclass"]
            name_superclass = tex_command["name_superclass"]

            # You can only define a class once
            if name_subclass in all_names_set:
                raise TraceableExperimenTeXError(
                    tex_command["tex_filename"],
                    tex_command["tex_node"],
                    "Subclass name already exists: %s. " % name_subclass
                )

            # Superclass must exist
            if name_superclass not in root_class_names_set and name_superclass not in tex_parsed_class_names:
                raise TraceableExperimenTeXError(
                    tex_command["tex_filename"],
                    tex_command["tex_node"],
                    "Super-class name does not exist: %s" % name_superclass
                )

            # Add to all the sets and lists
            all_names_set.add(name_subclass)
            all_names_list.append(name_subclass)
            tex_parsed_class_names.add(name_subclass)
            name_to_list_identifier_with_expline[name_subclass] = []
            if name_subclass not in name_to_list_expinclude_filename:
                name_to_list_expinclude_filename[name_subclass] = []
            name_to_parent_class_name[name_subclass] = name_superclass
            if name_superclass not in root_class_names_set:
                tex_parsed_class_names_which_have_been_extended.add(name_superclass)
            name_to_child_names[name_subclass] = []
            name_to_child_names[name_superclass].append(name_subclass)

        elif tex_command["tex_command"] == "expinstance":
            name_inst = tex_command["name_inst"]
            name_superclass = tex_command["name_superclass"]

            # You can only define a class once
            if name_inst in all_names_set:
                raise TraceableExperimenTeXError(
                    tex_command["tex_filename"],
                    tex_command["tex_node"],
                    "Instance name already exists: %s. " % name_inst
                )

            # Superclass cannot be an instance
            if name_superclass in instance_names:
                raise TraceableExperimenTeXError(
                    tex_command["tex_filename"],
                    tex_command["tex_node"],
                    "Super must be a class, not an instance: %s" % name_superclass
                )

            # Superclass must exist
            if name_superclass not in root_class_names_set and name_superclass not in tex_parsed_class_names:
                raise TraceableExperimenTeXError(
                    tex_command["tex_filename"],
                    tex_command["tex_node"],
                    "Super-class name does not exist: %s" % name_superclass
                )

            # Add to all the sets and lists
            all_names_set.add(name_inst)
            all_names_list.append(name_inst)
            instance_names.add(name_inst)
            name_to_list_identifier_with_expline[name_inst] = []
            if name_inst not in name_to_list_expinclude_filename:
                name_to_list_expinclude_filename[name_inst] = []
            name_to_parent_class_name[name_inst] = name_superclass
            if name_superclass not in root_class_names_set:
                tex_parsed_class_names_which_have_been_extended.add(name_superclass)
            name_to_child_names[name_inst] = []
            name_to_child_names[name_superclass].append(name_inst)

        elif (
                tex_command["tex_command"] == "expincludetext" or
                tex_command["tex_command"] == "expincludegraphics"
        ):
            name_inst = tex_command["name_inst"]

            # We optimistically add it, and later afterwards check if it is indeed
            # an instance. This is because for formatting reasons, includes are before the experiment
            # instance is even declared.
            if name_inst not in name_to_list_expinclude_filename:
                name_to_list_expinclude_filename[name_inst] = []
            name_to_list_expinclude_filename[name_inst].append(tex_command["expinclude_filename"])

        else:
            raise ValueError("TeX command " + str(tex_command["tex_command"]) + " does not exist.")

    # All classes must have been extended
    if tex_parsed_class_names != tex_parsed_class_names_which_have_been_extended:
        raise ExperimenTeXError(
            "The following TeX parsed classes have not been extended at all: %s"
            % str((tex_parsed_class_names.difference(tex_parsed_class_names_which_have_been_extended)))
        )

    # Forward declaration of an exp-name is permitted for plot filenames as they sometime need to be used earlier
    # for formatting reasons
    for exp_name in name_to_list_expinclude_filename.keys():
        if exp_name not in all_names_set:
            raise ExperimenTeXError(
                "Output plot file %s was requested for a non-existent experiment name: %s" % (
                    name_to_list_expinclude_filename[exp_name],
                    exp_name
                )
            )

    # Cannot have an output plot file for a non-instance
    for exp_name in name_to_list_expinclude_filename.keys():
        if len(name_to_list_expinclude_filename[exp_name]) != 0 and exp_name not in instance_names:
            raise ExperimenTeXError(
                "Output plot file %s was requested for a non-instance experiment name: %s" % (
                    name_to_list_expinclude_filename[exp_name],
                    exp_name
                )
            )

    # Print out statistics
    print("  > # of root classes......... %d" % len(root_class_names_set))
    print("  > # of TeX parsed classes... %d" % len(tex_parsed_class_names))
    print("  > # of instances............ %d" % len(instance_names))

    # Print out hierarchy visually
    print("  > Hierarchy visual display:")
    print("--------------------------------------------------------")
    print("")
    for root_class_name in root_class_names_list:
        to_visit = [(0, root_class_name)]
        while len(to_visit) != 0:
            u = to_visit.pop(0)
            s = ""
            num_spaces = 0
            for i in range(0, u[0]):
                num_spaces += (1 + i)
            for i in range(num_spaces):
                s += " "
            for i in range(u[0]):
                s += ">"
            if u[0] == 0:
                print("ROOT: %s" % u[1])
            else:
                if u[1] in tex_parsed_class_names:
                    explines_str = "expline" + ("s" if len(name_to_list_identifier_with_expline[u[1]]) > 1 else "")
                    print("%s Class %s has %d %s" % (
                        s,
                        u[1],
                        len(name_to_list_identifier_with_expline[u[1]]),
                        explines_str
                    ))
                else:
                    explines_str = "expline" + ("s" if len(name_to_list_identifier_with_expline[u[1]]) > 1 else "")
                    expincludes_str = "expinclude" + ("s" if len(name_to_list_expinclude_filename[u[1]]) > 1 else "")
                    print("%s Experiment %s has %d %s (and %d output plot file %s including duplicates)" % (
                        s,
                        u[1],
                        len(name_to_list_identifier_with_expline[u[1]]),
                        explines_str,
                        len(name_to_list_expinclude_filename[u[1]]),
                        expincludes_str
                    ))
            if u[1] in name_to_child_names:
                for v in name_to_child_names[u[1]]:
                    to_visit.insert(0, (u[0] + 1, v))
        print("")
    print("--------------------------------------------------------")
    print("")

    return name_to_child_names, name_to_list_identifier_with_expline, name_to_list_expinclude_filename


def parse(tex_filenames):
    experimentex_commands_list = parse_tex_files(tex_filenames)
    return process_inheritance(experimentex_commands_list)
