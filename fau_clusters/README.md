# FAU's High Performance Computing (HPC) Cluster

## Cluster Information
Website: https://hpc.fau.edu/ <br>
Dashboard: https://ondemand.hpc.fau.edu/

## Navigating the OnDemand Dashboard
There are two primary locations within the OnDemand Dashboard:

**1) The File System** <br>

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src="https://user-images.githubusercontent.com/34531896/195513452-796e93d2-2bee-4b65-84fc-e566b0892c54.png" width='250' height='50'> <br>

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;The OnDemand File System contains all files accessible by the cluster. <br>

**2) The KoKo Shell**

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src="https://user-images.githubusercontent.com/34531896/195514503-eb2a328e-38df-4904-bd5c-a7e4ce08e8a1.png" width='250' height='50'> <br>

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;The KoKo Shell allows the user to interact with the cluster through the command line. <br>

## Anaconda Installation
Before DeepLabCut is installed, it is essential to install Anaconda. This can be done via the KoKo Shell.

Tutorial:
1. <code>wget https://repo.anaconda.com/archive/Anaconda3-2022.05-Linux-x86_64.sh</code>
2. <code>chmod u+x Anaconda3-2022.05-Linux-x86_6.sh</code>
3. <code>./Anaconda3-2022.05-Linux-x86_6.sh</code>
4. Accept all Anaconda terms and confirm Anaconda installation location
5. <code>source .bashrc</code>

## DeepLabCut Installation
In the same KoKo shell, DeepLabCut can now be installed.

Tutorial:<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Note: Steps 4-7 are from https://www.tensorflow.org/install/pip.
1. <code>salloc --exclusive</code>
2. <code>srun conda create –name deeplabcut python=3.8</code>
3. <code>conda activate deeplabcut</code>
4. <code>srun conda install -c conda-forge cudatoolkit=11.2 cudnn=8.1.0</code>
5. <code>export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$CONDA_PREFIX/lib/</code>
6. <code>mkdir -p $CONDA_PREFIX/etc/conda/activate.d</code>
7. <code>echo 'export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$CONDA_PREFIX/lib/' > $CONDA_PREFIX/etc/conda/activate.d/env_vars.sh</code>
8. <code>srun pip install deeplabcut</code>
9. <code>srun pip install --upgrade tensorflow==2.9.2</code>
10. <code>srun pip install --upgrade numpy==1.22</code>
11. <code>srun python3 -c “import deeplabcut”</code>

## Analyzing New Videos with DLC
The resources of the cluster can be distributed to quickly and efficiently use a trained DeepLabCut model to analyze multiple new movies.

Tutorial:
1. Navigate to the file path
2. <code>sbatch submit_dlc.sh run_dlc_analysis.py</code>
3. <code>squeue -u $USER</code> (use this to check current progress)

## Miscellaneous Commands

* <code>gnodes</code>
* <code>gnodes -h</code>
* <code>gnodes -p shortq7</code>
