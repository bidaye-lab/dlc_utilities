# DLC and remote clusters
FAU offers and maintains high-performance computing (HPC) clusters, which can be used to outsource DLC computations.
The current folder collects all that is necessary to run DLC on these clusters.

## Requesting access to the clusters
The clusters are available to MPFI, but access has to be explicitly requested for each user on the [FAU HPC](https://hpc.fau.edu/) website.
The account comes with an email address, which is used for communication with the admins (emails to all users, FAU IT tickets).

## Available resources 
DLC profits heavily from the use of GPUs.
As of Oct 2022, the cluster offers
- NVIDIA A100 on nodes `nodeamd[039-041]`, 3 GPUs per node
- NVIDIA V100 on nodes `nodenviv100[01-13]`, 4 GPUs per node

A major drawback is that single GPU calculations are currently limited to 6 h.
Since DLC cannot use multiple GPUs simultaneously, the DLC calculations have to be designed in a way that they finish within 6 h.
For training, this implies restarting from the latest snapshot.
For analysis, this implies limiting the number of videos.

# Running DLC calculations
The most convenient way to work with the cluster is via the web browser.
The clusters are accessible via the [OnDemand Dashboard](https://ondemand.hpc.fau.edu/),
which supplies a file browser and a command line:
- file browser
<img src="https://user-images.githubusercontent.com/34531896/195513452-796e93d2-2bee-4b65-84fc-e566b0892c54.png" width='250' height='50'>
- command line (KoKo shell)
<img src="https://user-images.githubusercontent.com/34531896/195514503-eb2a328e-38df-4904-bd5c-a7e4ce08e8a1.png" width='250' height='50'>

The file browser can be used to upload and download files to the home directory of the user.
Carefull: The home directory has a quota of 300 GB. 
For intermediate storage of larger datasets, use the directory `/mnt/beegfs/scratch`.
This does not have a quota, but will be deleted if the entire cluster runs out of storage space.

Using the web browser-based file explorer and command line can become cumbersome for routine data pipelines.
The [FAU HPC](https://hpc.fau.edu/2013/07/20/transferring-files/) website explains possibilities transfer data from and to the cluster.

## Submitting DLC jobs
The clusters pool many computational resources and make them available to many users simultaneously.
To assure a fair distribution, one makes use of a workload manager. 
The FAU clusters use the [slurm workload manager](https://slurm.schedmd.com/).
Certain commands, such as `sbatch` or `sinfo`, are specific to this workload manager. 
The [FAU HPC](https://hpc.fau.edu/) website is a good resource on how to use slurm.

### Helpful commands
- show current usage of all nodes `gnodes` (has to be [downloaded](https://github.com/birc-aeh/slurm-utils/blob/master/gnodes) first)
- show current jobs `squeue -u $USER`
- show all available slurm partitions `sinfo`

### Analyzing New Videos with DLC
Assuming that the DLC model has been trained, new videos can be analyzed with the following steps:

1. Place `submit_dlc.sh` and `run_dlc_analysis.py` in the project folder
2. Adjust the file paths in the `run_dlc_analysis.py` and `config.yaml`
3. Navigate to the project folder in the shell
4. Call `sbatch submit_dlc.sh run_dlc_analysis.py` (assumes both files to be in the project folder)

All output from DLC is written in the `<submitscript>.<jobid>.out` file (`python` errors as well). 
The corresponding `.err` file contains only errors from slurm.


# Installing DLC on the clusters
The following instructions will install DLC using a user-specific Anaconda installation.
None of the `Anaconda`/`CUDA`/`cuDNN` modules available on the cluster will be used.

Carry out the following steps in the same KoKo shell to install DLC.

## Install Anaconda
1. Download: `wget https://repo.anaconda.com/archive/Anaconda3-2022.05-Linux-x86_64.sh` (place link to latest version here)
2. Install: `sh Anaconda3-2022.05-Linux-x86_6.sh`
3. Accept all terms and confirm installation location
4. Say yes the question whether conda should be initialized 
5. Activate by logging out and in or calling `source ~/.bashrc`

## Install CUDA and cuDNN

1. Request one of the nodes to avoid using the login node: `salloc --exclusive`
2. Create: `srun conda create –name deeplabcut python=3.8`
3. Activate: `conda activate deeplabcut`
4. Install `CUDA` and `cuDNN`: `srun conda install -c conda-forge cudatoolkit=11.2 cudnn=8.1.0`\*
5. Make libraries available: `export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$CONDA_PREFIX/lib/` 
6. Make libraries available: `mkdir -p $CONDA_PREFIX/etc/conda/activate.d`
7. Make libraries available: `echo 'export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$CONDA_PREFIX/lib/' > $CONDA_PREFIX/etc/conda/activate.d/env_vars.sh`

\*Note: Each `tensorflow` version requires specific `CUDA` and `cuDNN` versions (see [Tested build configurations](https://www.tensorflow.org/install/source#tested_build_configurations)). 
Steps 4-7 are adapted from the [tensorflow website](https://www.tensorflow.org/install/pip).

## Install DLC
9. Install DLC via `pip`: `srun pip install deeplabcut`
10. Downgrade `tensorflow`: `srun pip install --upgrade tensorflow==2.9.2`\*
11. Downgrade `numpy`: `srun pip install --upgrade numpy==1.22`\*
12. Verify installation: `srun python3 -c “import deeplabcut”`

\*Note: Currently, only `tensorflow` version 2.9.2 works on the clusters and `numpy` version 1.23 breaks DLC.


