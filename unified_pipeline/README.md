# Unified Pipeline

Combines previous DLC, preprocessing, and Anipose scripts into one pipeline to make it easier to convert raw video files into 3D Anipose annotations. The pipeline will run DLC, preprocess DLC-generated data, and then call anipose to generate 3D annotations. Note: this pipeline is intended for ball data, it does not currently support slipery surface data.

## Installation

1. Install [DeepLabCut](https://deeplabcut.github.io/DeepLabCut/docs/installation.html) and [Anipose](https://anipose.readthedocs.io/en/latest/installation.html) 
    - run `conda activate <deeplabcut-env-name>` and then `pip install datetimerange` to install the datetimerange library in the deeplabcut environment. 
2. Install [Anipose](https://anipose.readthedocs.io/en/latest/installation.html)
    - TODO install `jupyterlab` or similar to use jupyter notebooks

Note: Anipose may not be compatible with more recent default openCV installations. Installation with openCV 4.6 was tested. In case of trouble with openCV, run
```
conda activate anipose
pip install opencv-python==4.6.0.66
pip install opencv-contrib-python==4.6.0.66
```

3. Clone the repository

    Note: Since the unified pipeline code is not on the main branch of this repository but instead on the `unified-workflow` branch, if you are using the command line interface to clone it, make sure to specify the branch when running the clone command.
    To clone this branch specifically: `git clone -b unified-workflow <the URL to this repository>`

4. Install local modules
    - Once you have cloned the repo, enter the directory you cloned into and run `pip install -e .` (Make sure you have the Anaconda environment active) 



## Usage

1. Run through the `DLC_pipeline` notebook, making sure to enter values into any user variables (these will be pointed out by comments).
    - Use the `DEEPLABCUT` environment you created.
    - All config and other common files should be stored in `./common_files` (relative to script)
    - Configuration files include `calibration_target.yml`, `calibration_timeline.yml`, `GenotypeFly-G.h5`, `config_fly.toml` or `config_board.toml`, `dlc_networks.yml` (Names should be exact for now, since some are hardcoded in.)
    - Remember that this pipeline only works for ball data.
2. Run through the `Anipose_pipeline` notebook, making sure to enter values into any user variables.
    - Use the `anipose` environment you created.

### Note
The pipeline will find all folders (in the specified parent directory) that have ungenerated Anipose/DLC and run generation on all of them.

## For development

- Make sure hardcoded root path matches
- To rerun Anipose preprocessing delete the generated `Anipose` folder only!
- If you run DLC I would recommend to backup the DLC output so you can rerun the preprocessing steps without rerunning DLC every time
- If DLC Has already been run don't rerun the DLC cell otherwise it will take several hours to run
