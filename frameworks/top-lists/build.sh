#!/bin/bash

# Extract the raw data
tar -xzf analysis_qs_timedelta.tar.gz || exit 1

# Plot the original 2c figure
python3 plot_original_2c.py pdf || exit 1

# Generate the data for all new plots
python3 generate_data.py data || exit 1
