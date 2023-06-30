# Unified Pipeline

Combines previous DLC, preprocessing, and Anipose scripts into one pipeline to make it easier to convert raw video files into 3D Anipose annotations. The pipeline will run DLC, preprocess DLC-generated data, and then call anipose to generate 3D annotations.

## Usage

1. Run through the `DLC_pipeline` notebook, making sure to enter values into any user variables.
    - All config and other common files should be stored in `./common_files` (relative to script)
2. Run through the `Anipose_pipeline` notebook, making sure to enter values into any user variables.

