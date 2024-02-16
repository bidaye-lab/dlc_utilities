# DLC/Anipose Pipeline

This workflow collects all steps necessary to reconstruct the 3D fly pose from 2D video data.

The individual steps are:
- annotate video files with DeepLabCut (DLC)
- preprocess the DLC output to be compatible with Anipose
- run Anipose to generate 3D reconstructions

Note: Currently, only fly-on-the-ball recordings are supported, slippery surface is not yet implemented.

# Usage
The pipeline is separated into two parts, which are explained in the respective notebooks:
|file|description|
|---|---|
|[`DLC_pipeline.ipynb`](scripts/DLC_pipeline.ipynb)|Annotate video files with DeepLabCut|
|[`Anipose_pipeline.ipynb`](scripts/Anipose_pipeline.ipynb)|Preprocess DLC output for Anipose and run Anipose|

# Installation
## Prerequisites
- Install [git](https://git-scm.com/downloads)
- Install
[DeepLabCut](https://deeplabcut.github.io/DeepLabCut/docs/installation.html),
then run
```
conda activate <deeplabcut-env-name>
pip install datetimerange
```
- Install
[Anipose](https://anipose.readthedocs.io/en/latest/installation.html) 
into a separate conda environment, then run
```
conda activate <anipose-env-name>
pip install jupyter opencv-python==4.6.0.66 opencv-contrib-python==4.6.0.66
```

Note: Anipose may not be compatible with more recent default openCV installations. Installation with openCV 4.6 was tested.


## Installing pipeline code

Clone this repo and install code as local package
```
git clone https://github.com/bidaye-lab/dlc_utilities/
cd dlc_utilities
conda activate <deeplabcut-env-name>
pip install -e .
conda activate <anipose-env-name>
pip install -e .
```