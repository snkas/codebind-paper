#!/bin/bash

# YOU SHOULD NOT NEED TO EDIT THIS FILE UNLESS YOU HAVE A MORE SOPHISTICATED
# WAY OF PERFORMING THE RUNS

# In this step, we go over all the run directories and execute the run.sh
# executable in it to run. Of course, this could also be done in parallel,
# or with a job scheduler. We trust that the run.sh if it has already been
# run just simply exit(0) instead of rerunning itself.

for run_dir in temp/runs/*/ ; do
    if test -f "${run_dir}run.sh"; then
       echo "Running: ${run_dir}" || exit 1
       cd ${run_dir} || exit 1
       bash run.sh || exit 1
       cd ../../.. || exit 1
    else
       echo "Directory in temp/runs does not have a run.sh: ${run_dir}" || exit 1
       exit 1
    fi
done
