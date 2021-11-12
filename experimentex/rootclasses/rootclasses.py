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

######################################################################
# ROOT CLASSES
#
# Below you must define all the root classes which are used throughout
# the TeX. Each root class must have a name, an interpreter to interpret
# explines and generate the runs, and a plotter to plot the expinclude files.

from rootclasses.rootclass_mmfa import MmfaRootClassInterpreter, MmfaRootClassPlotter
from rootclasses.rootclass_one_link_tcp import OneLinkTcpRootClassInterpreter, OneLinkTcpRootClassPlotter
from rootclasses.rootclass_load_ls import LoadLeafSpineRootClassInterpreter, LoadLeafSpineRootClassPlotter
from rootclasses.rootclass_top_lists import TopListsRootClassInterpreter, TopListsRootClassPlotter

root_classes = [
    ("mmfa", MmfaRootClassInterpreter(), MmfaRootClassPlotter()),
    ("one-link-tcp", OneLinkTcpRootClassInterpreter(), OneLinkTcpRootClassPlotter()),
    ("load-ls", LoadLeafSpineRootClassInterpreter(), LoadLeafSpineRootClassPlotter()),
    ("top-lists", TopListsRootClassInterpreter(), TopListsRootClassPlotter()),
]

######################################################################
######################################################################
######################################################################
######################################################################
######################################################################
# Below here you should not edit as they are just helper functions


def retrieve_root_class_names_list():
    root_class_names_list = []
    for root_class in root_classes:
        root_class_names_list.append(root_class[0])
    return root_class_names_list


def get_root_class_interpreter(root_class_name):
    for root_class in root_classes:
        if root_class[0] == root_class_name:
            return root_class[1]
    raise ValueError("Could not find interpreter for undefined root class name: %s" % root_class_name)


def get_root_class_plotter(root_class_name):
    for root_class in root_classes:
        if root_class[0] == root_class_name:
            return root_class[2]
    raise ValueError("Could not find plotter for undefined root class name: %s" % root_class_name)
