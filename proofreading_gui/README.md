# Proofreading GUI

A simple GUI built using Python's tkinter package which allows drag-and-drop movement of DLC assigned joint positions. The built in `ErrorDetection.py` provides a comprehensive error detection system which checks for smoothness in the joint angles movements.

## Installation

1. Make sure Python is installed on your system with `python --version`
    - This script is tested for Python 3.10.0+ and may not work on older versions.

2. Clone the repository
    - Since this will not be on the main branch please specify the branch name
    - `git clone -b proofreading-gui <repository-url>` 

3. Create a vertual or conda environment
    - Recommended: `python -m venv .venv`
    - Activate the environment with `.venv/scripts/activate`

4. Run `pip install -r requirements.txt` to install requirements

## Usage

1. To use the GUI simply type `python main.py`

2. There are two locations with output data
    - For corrected CSVs and h5 files check the folder with corrected-pose-2d. The path of this folder depends on your input. Ex. If the script is run on N3 and trial3 than the path will be like input-folder\anipose\project\N3\trial3\corrected-pose-2d.
    - For log/debug data check the input-folder\proofreader-output_{genotype}N{number}\{trial_if_any}. The trial subfolder only exists when there are multiple trials.


## Note

Soon there will be an .exe which allows this to be run like any other application without any setup. This application also requires a moderately specific file structure. If you experience any problems with this application please send the input-folder\proofreader-output-{genotype}-N{number}\proofreader_log_{date}.log


