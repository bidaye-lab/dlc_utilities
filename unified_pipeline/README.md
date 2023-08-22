# Unified Pipeline

Combines previous DLC, preprocessing, and Anipose scripts into one pipeline to make it easier to convert raw video files into 3D Anipose annotations. The pipeline will run DLC, preprocess DLC-generated data, and then call anipose to generate 3D annotations. Note: this pipeline is intended for ball data, it does not currently support slipery surface data.

## Installation

1. Install [DeepLabCut](https://deeplabcut.github.io/DeepLabCut/docs/installation.html) and [Anipose](https://anipose.readthedocs.io/en/latest/installation.html) into separate Anaconda environments (e.g `DEEPLABCUT` and `Anipose`)
2. Run `conda activate <deeplabcut-env-name>` and then `pip install datetimerange` to install the datetimerange library in the deeplabcut environment. 

## Usage

1. Run through the `DLC_pipeline` notebook, making sure to enter values into any user variables (these will be pointed out by comments).
    - Use the `DEEPLABCUT` environment you created.
    - All config and other common files should be stored in `./common_files` (relative to script)
    - Configuration files include `calibration_target.yml`, `calibration_timeline.yml`, `GenotypeFly-G.h5`, `config_fly.toml` or `config_board.toml`, `dlc_networks.yml` (Names should be exact for now, since some are hardcoded in.)
    - Remember that this pipeline only works for ball data.
2. Run through the `Anipose_pipeline` notebook, making sure to enter values into any user variables.
    - Use the `anipose` environment you created.

