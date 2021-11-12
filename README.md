# CodeBind paper

[![build](https://github.com/snkas/codebind-paper/workflows/build/badge.svg)](https://github.com/snkas/codebind-paper/actions?query=workflow%3Abuild+branch%3Amaster)

This repository can be used to replicate the paper "CodeBind: tying networking papers to their experiment code".

_This code repository makes use of [ns-3](https://www.nsnam.org/), the [basic-sim](https://github.com/snkas/basic-sim) ns-3 module, [top-lists](https://doi.org/10.1145/3278532.3278574) (by Scheitle et al., 2018), [ACM LaTeX class files](https://www.acm.org/publications/proceedings-template), and several gnuplot files. See the complete license at [./LICENSE](./LICENSE) for more detailed information. It moreover makes use of several distribution packages (texlive, gnuplot, openmpi, lcov) and Python modules (texsoup, [exputilpy](https://github.com/snkas/exputilpy), networkx, matplotlib, pandas, numpy, statsmodels)._


## Video demo

We have prepared a short (5:31) video demonstration of CodeBind, which is uploaded to an Google account (to have a video player):

https://drive.google.com/file/d/1f8gu3MpWzXM4WbpFLy7DXDcR4z3s6Ws9/view

(Make sure to manually set the quality to 720p or 1080p in the player -- the default is 360p)

**Note:** new max-min fairness and congestion control experiments run as quick as in the video under mild parameter changes. The leaf-spine load experiments (not shown in video) are heavy experiments that consume a large amount of time to rerun with new parameters (~8 hours on single core). See the instructions below for more information on reproduction duration.


## Using CodeBind for your own paper

This repository is to reproduce the CodeBind complete paper including all its showcases. If you would like to use CodeBind for your own paper: we have prepared a template repository that you can use as a starting point:

https://github.com/snkas/codebind-template

It contains more explanation on how to create your own experiments, and its use is probably more convenient than having to strip away the experiment pipeline of the three showcases which are in this repository.


## Reproducing this paper

1. Make sure you are on Ubuntu LTE 18.04, 20.04 or later, with Python version 3.7+ installed.
   You can verify with the following commands:
   * `python3 --version`
   * `python3 -m pip --version` (installable via `sudo apt install python3-pip`)
   
2. Clone this repository (*estimated duration: 2-3 min*):
   ```
   git clone https://github.com/snkas/codebind-paper.git
   cd codebind-paper
   ```

3. Setup the environment (i.e., install dependencies) (*estimated duration: 7-8 min*):
   ```
   bash setup_env.sh
   ```
   
   ... which should install all dependencies necessary, among which 
   distribution packages (texlive, gnuplot, openmpi, lcov) and
   Python modules (texsoup, exputilpy, networkx, matplotlib, pandas, numpy, statsmodels).
   
   Primary time consumer: TeX Live packages (5-6 min)

4. **(Optional but recommended)** It takes some time (~8 hours) to rerun all the leaf-spine load runs in the next step.
   We provide an archive with most of the runs already finished (except one, to verify that it can be run), for convenience.
   To extract:
   ```
   mkdir -p temp
   tar -xzf partial-temp-runs.tar.gz -C temp
   ```

5. Reproduce the paper (*estimated duration (assuming step 4 was done): 15-20 min*): 
   ```
   bash reproduce.sh
   ```
   Primary time consumers: build ns-3 (7-8 min), top-lists data processing (3-4 min), run one of the leaf-spine load runs (4-5 min)
   
6. The paper is output at: `paper-latex/out/paper.pdf`


## Editing this paper via LaTeX

1. The following sections have ExperimenTeX in them:
   * `paper-latex/02-example.tex`
   * `paper-latex/05-cc-showcase.tex`
   * `paper-latex/06-netload-showcase.tex`
   * `paper-latex/07-toplists-showcase.tex`
   
2. We welcome readers to edit these above LaTeX files. For example, change the random packet loss in `paper-latex/05-cc-showcase.tex` from `0.001%` to `1%`, and see what happens in that setting to the metrics and figures in the paper.

3. You can recreate the paper by executing the same steps again as above (in particular: `bash reproduce.sh`)


## More information about the implementation

1. There are four root experiment classes (defined in `experimentex/rootclasses/rootclasses.py`):
   * mmfa (`experimentex/rootclasses/rootclass_mmfa.py`)
   * one-link-tcp (`experimentex/rootclasses/rootclass_one_link_tcp.py`)
   * load-ls (`experimentex/rootclasses/rootclass_load_ls.py`)
   * top-lists (`experimentex/rootclasses/rootclass_top_lists.py`)

2. There are three frameworks:
   * mmfa (`frameworks/mmfa`) -- used by the mmfa root experiment class (they have the same name, but this is not required)
   * ns-3 basic-sim (`frameworks/ns-3-bs`) -- used by one-link-tcp and load-ls root experiment classes
   * top-lists (`frameworks/top-lists`) -- used by top-lists root experiment class 
