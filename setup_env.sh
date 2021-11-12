#!/bin/bash

# Below you must setup the whole environment needed
# for the run frameworks starting from scratch:
# - Packages
# - Python packages
# - ...
#
# All external dependencies must be installed in this script.

# Update
sudo apt-get update || exit 1

# ExperimenTeX parser
python3 -m pip install texsoup || exit 1  # For the parser
cd experimentex/exputilpy || exit 1  # Utility Python module used in many places
python3 -m pip install . || exit 1
cd ../.. || exit 1

# PDF compilation
sudo apt-get -y install texlive-base texlive-binaries texlive-extra-utils texlive-fonts-recommended texlive-fonts-extra texlive-latex-base texlive-latex-extra texlive-latex-recommended texlive-pictures texlive-plain-generic texlive-science || exit 1

# Gnuplot
sudo apt-get -y install gnuplot || exit 1

# ns-3 (including contribution module basic-sim)
sudo apt-get -y install openmpi-bin openmpi-common openmpi-doc libopenmpi-dev lcov || exit 1
python3 -m pip install numpy || exit 1
python3 -m pip install statsmodels || exit 1

# max-min fairness (mmfa)
python3 -m pip install networkx || exit 1

# top-lists
python3 -m pip install matplotlib || exit 1
python3 -m pip install pandas || exit 1
