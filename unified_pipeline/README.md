# Unified Pipeline

Combines DeepLabCut (DLC), preprocessing, and Anipose scripts into a single pipeline for converting raw multi-camera video files into 3D Anipose reconstructions.

The pipeline currently supports data collected across four experiment conditions:
- **Ball** — fly walking on a spherical treadmill
- **SS** — flat 'slippery' surface
- **Air** — air suspended
- **Amp** — suspended fly with all legs amputated at the femur midpoint

The pipeline runs entirely from a single Conda environment and performs:

```
Raw videos
    ↓
DeepLabCut analysis (Step 1)
    ↓
H-cam column preprocessing (Step 1b)
    ↓
DLC preprocessing / Anipose file structure generation (Step 2)
    ↓
Anipose triangulation (Step 3)
    ↓
Fixed-landmark postprocessing (Step 3b)
    ↓
Data structure generation (Step 4)
    ↓
Fly-centric coordinate transform (Step 5)
    ↓
Metric rescaling to mm (Step 6)
```

---

## Required Files and Folder Structure

### Input data

The pipeline expects experiment data organized as:

```
<root>/
  N1/
    Ball/    ← MP4 video files
    SS/
    Air/
    Amp/
  N2/
  ...
```

### Repository layout

```
unified_pipeline/
├── settings.toml                   # Main config: videos_path, root, common_files paths
├── config.py                       # Loads settings via dynaconf
├── common_files/                   # Shared config and reference files (see below)
├── pipeline/
│   ├── pipeline_step_1.py          # Step 1+2: DLC analysis + anipose file prep
│   └── pipeline_step_2.py          # Step 3: Anipose triangulation
├── src/
│   ├── preprocess.py               # Step 1b: H-cam column append
│   ├── dlc.py                      # analyze_new(): runs DLC inference
│   ├── clean.py                    # Preprocessing functions on DLC CSVs
│   ├── hdf.py                      # Converts preprocessed DataFrames to HDF5
│   ├── calibration.py              # Calibration type resolution
│   ├── file_tools.py               # IO utilities
│   ├── postprocess_anipose.py      # Step 3b: fixed-landmark median replacement
│   ├── datastructure.py            # Step 4: data structure generation
│   ├── coordinate_transform.py     # Step 5: fly-centric coordinate transform
│   ├── rescale.py                  # Step 6: metric rescaling to mm
│   └── pipeline_queue.py           # Multi-folder queue with checkpointing
└── scripts/
    ├── DLC_pipeline.ipynb          # Main notebook (Steps 1–6)
```

### Required common files

All common files must be placed in `common_files/` relative to the repository root:

| File | Purpose |
|------|---------|
| `DLC_network_sets.yml` | DLC model paths per condition (Ball/SS/Amp/Air) and camera (A–H) |
| `calibration_target.yml` | Maps directories to board vs fly calibration type |
| `calibration_timeline.yml` | Maps date ranges to calibration file locations |
| `config_board.toml` | Anipose config for board-based calibration |
| `config_fly.toml` | Anipose config for fly-based calibration |
| `GenotypeFly-G.h5` | Dummy HDF5 file for camera G (not tracked by DLC) |
| `SS_preprocess_extracols.csv` | Reference columns for H-cam SS preprocessing (Step 1b) |
| `Air_preprocess_extracols.csv` | Reference columns for H-cam Air preprocessing (Step 1b) |

Filenames must match exactly — several are hardcoded in the pipeline.

### `settings.toml`

```toml
videos_path = 'C:\path\to\your\data'
common_files = "../common_files"
```
---

## Installation

The pipeline runs from a single Conda environment named `unified_pipeline`.

Tested on Windows with Python 3.10, DeepLabCut 2.3.11, TensorFlow 2.10, and Anipose 1.1.24.

### 1. Create the Conda environment

```bash
conda create -n unified_pipeline python=3.10 pip -y
conda activate unified_pipeline
```

### 2. Prevent external user-site packages from entering the environment

```bash
conda env config vars set PYTHONNOUSERSITE=1
conda deactivate
conda activate unified_pipeline
```

### 3. Install numerical and TensorFlow dependencies

```bash
python -m pip install numpy==1.26.4
python -m pip install protobuf==3.19.6
python -m pip install tensorflow==2.10.0 tensorflow-estimator==2.10.0 keras==2.10.0 tensorboard==2.10.1
```

### 4. Install OpenCV

Install only `opencv-contrib-python`. 

```bash
python -m pip install opencv-contrib-python==4.11.0.86
```

`opencv-contrib-python` is required (not the plain `opencv-python`) because Step 6 uses ArUco marker detection for auto board reconstruction.

### 5. Install DeepLabCut

```bash
python -m pip install deeplabcut==2.3.11
python -m pip install tensorpack==0.11
python -m pip install tf-slim==1.1.0
```

The message `DLC loaded in light mode; you cannot use any GUI` is expected when running without GUI dependencies and does not affect pipeline analysis.
Note that the current DLC config files are not compatible with DLC releases >3 since these do not support multiple predictions per keypoint. 

### 6. Install Anipose

```bash
python -m pip install aniposelib==0.8.0
python -m pip install anipose==1.1.24
```

### 7. Install pipeline-specific dependencies

```bash
python -m pip install dynaconf
python -m pip install datetimerange
```

### 8. Install Jupyter support

```bash
python -m pip install jupyter ipykernel
python -m ipykernel install --user --name unified_pipeline --display-name "Python (unified_pipeline)"
```

When opening notebooks in VS Code or Jupyter, select **Python (unified_pipeline)** as the kernel.

### 9. Install FFmpeg

```bash
conda install -c conda-forge ffmpeg -y
```

### 10. Clone the repository

```bash
git clone -b unified-workflow <repository-url>
cd dlc_utilities/unified_pipeline
```

### 11. Install the local pipeline modules

From the `unified_pipeline` directory with the environment active:

```bash
python -m pip install -e . --no-deps
```

`-e` installs in editable mode so local source changes take effect immediately. `--no-deps` prevents the local package from overwriting the pinned dependency versions.

### 12. Verify the installation

```bash
python -c "import tensorflow as tf; import deeplabcut; import anipose; print('TF:', tf.__version__); print('DLC:', deeplabcut.__version__); print('Anipose OK')"
```

Expected:

```text
TF: 2.10.0
DLC: 2.3.11
Anipose OK
```

```bash
python -c "from config import settings; print('Config OK')"
```

---

## Tested Environment

```text
Python                  3.10
NumPy                   1.26.4
DeepLabCut              2.3.11
TensorFlow              2.10.0
tensorflow-estimator    2.10.0
Keras                   2.10.0
TensorBoard             2.10.1
protobuf                3.19.6
tensorpack              0.11
tf-slim                 1.1.0
opencv-contrib-python   4.11.0.86
Anipose                 1.1.24
aniposelib              0.8.0
dynaconf                (latest)
datetimerange           (latest)
```

Avoid upgrading TensorFlow, NumPy, protobuf, or OpenCV independently — these packages have tightly coupled version requirements.

---

## Usage

### 1. Activate the environment

```bash
conda activate unified_pipeline
```

For notebooks, select **Python (unified_pipeline)** as the Jupyter kernel.

### 2. Configure settings

Edit `settings.toml` to point `videos_path` at the root directory containing your experiment folders (`N1/`, `N2/`, etc.).

### 3. Run the pipeline

Open `scripts/DLC_pipeline.ipynb` and run through the cells, setting user variables where indicated. This notebook runs all pipeline steps (1 through 6) sequentially.

The pipeline finds all experiment folders under the configured path that have not yet had the relevant outputs generated and processes them automatically. Use the queue section at the end of the notebook to batch-process multiple folders.

---
## Notes on requirements
1. Data acquisition using JSPIN does not add a timestamp to the end of movie files. For folders with such data, deposit a text file *'calib_date.txt'* with single line entry "date: mmddyyyy". This date will be matched with the calibration timelines to find the corresponding calibration file.
2. Calibration movies should be acquired frequently and deposited in the BallSystem_CalibrationMov directory in the lab Z drive. These folders mimic the anipose folder structure. run 'anipose calibrate' in these folders to generate the calibration.toml file that will be copied over to the corresponding analysis folders while running this  pipeline. Only case when calibration is rerun at the time of analysis with this pipeline is using the fly as the calibration target. 
3. Step 6 is useful only when performing fly based calibration since board based calibration by default renders the fly in a metric space. 
4. If MATLAB based ball tracking is used and MAT files containing balltracking needs to be included in the datastuructures, deposit the MAT files in a 'BallTracking' folder in the parent directory and preprocess it to a 'BallVel' folder using matlab scrips (to be added here). The pipeline will look for this 'BallVel' folder in the parent directory if 'Ball' expeiment condition is found. 