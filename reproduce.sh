#!/bin/bash

# Usage help
if [[ "$1" == "--help" && "$#" -eq 1 ]]; then
  echo "Usage: bash reproduce.sh [--help]"
  exit 0
fi
if [[ "$#" -ne 0  ]]; then
  echo "Usage: bash reproduce.sh [--help]"
  exit 1
fi

echo "REPRODUCING..."
echo ""

echo "(Step 1/5) Building..."
bash step_1_build.sh || { echo "Build unsuccessful." 1>&2 ; exit 1; }
echo "(Step 1/5) Build is completed."

echo "(Step 2/5) Interpreting ExperimenTeX..."
bash step_2_interpret.sh || { echo "Interpreting ExperimenTeX failed." 1>&2 ; exit 1; }
echo "(Step 2/5) Paper ExperimenTeX is interpreted into runs."

echo "(Step 3/5) Executing runs..."
bash step_3_run.sh || { echo "Running failed." 1>&2 ; exit 1; }
echo "(Step 3/5) Runs are executed."

echo "(Step 4/5) Performing plotting..."
bash step_4_plot.sh || { echo "Plotting failed." 1>&2 ; exit 1; }
echo "(Step 4/5) Plots are made."

echo "(Step 5/5) Generating final PDF from LaTeX..."
bash step_5_pdf.sh || { echo "Generating final PDF failed." 1>&2 ; exit 1; }
echo "(Step 5/5) Final PDF is generated."

echo ""
echo "Paper has been reproduced."
echo ""
echo "Output PDF file: paper-latex/out/paper.pdf"
echo ""
#read -p "Would you like to open the final PDF? (y/n) " -n 1 -r
#echo ""
#if [[ $REPLY =~ ^[y]$ ]]
#then
#    xdg-open paper-latex/out/paper.pdf
#fi
