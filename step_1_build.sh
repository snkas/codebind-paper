#!/bin/bash

# Below you must perform the building of all
# the run frameworks that you make use of.
#
# This should only be running build and run scripts.
# External dependencies (e.g., from the Internet) should
# have already been retrieved in the setup_env.sh call.

# Max-min fair allocation (mmfa)
cd frameworks/mmfa || exit 1
python3 test_mmfa.py || exit 1
cd ../.. || exit 1

# ns-3
cd frameworks/ns-3-bs || exit 1
bash build.sh || exit 1
cd ../.. || exit 1

# top-lists
cd frameworks/top-lists || exit 1
bash build.sh || exit 1
cd ../.. || exit 1
