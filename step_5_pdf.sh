#!/bin/bash

# ONLY IF YOU HAVE A DIFFERENT LATEX BUILD PIPELINE DO YOU NEED TO EDIT THIS

# Below all the commands to actually finally build
# the paper should be executed (e.g., build pdf, build bibliography, ...)

cd paper-latex || exit 1
mkdir -p out || exit 1
pdflatex -output-directory out paper.tex || exit 1
cp *.bib out/ || exit 1
cp *.bst out/ || exit 1
cd out || exit 1
bibtex paper.aux || exit 1
cd .. || exit 1
pdflatex -output-directory out paper.tex || exit 1
pdflatex -output-directory out paper.tex || exit 1
cd .. || exit 1
