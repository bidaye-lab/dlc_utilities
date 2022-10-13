#!/bin/sh
#SBATCH --partition=shortq7
#SBATCH --gres=gpu
#SBATCH --nodes=1
#SBATCH --cpus-per-task=20
#SBATCH --output="%x.%j.out"
#SBATCH --error="%x.%j.err"

# output file as defined by slurm
OUT=${SLURM_JOB_NAME}.${SLURM_JOB_ID}.out

# SLURM submit script to run DLC with custom conda environment 
# not via modules

# print general slurm info
echo "HPC: Start time is $(date) $(date +%s)"
echo "HPC: SLURM_JOB_NAME is $SLURM_JOB_NAME"
echo "HPC: SLURM_SUBMIT_DIR is $SLURM_SUBMIT_DIR"
echo "HPC: SLURM_JOB_ID is $SLURM_JOB_ID"
echo "HPC: SLURM_NODELIST is $SLURM_NODELIST"
echo "HPC: SLURM_CPUS_PER_TASK is $SLURM_CPUS_PER_TASK"

# activate conda env
eval "$(conda shell.bash hook)"
conda activate deeplabcut

# execute task
echo "HPC: Running DLC..."
echo

# run DLC: $1 is python file
srun python $1 2>&1

# clean up output file (progress bars look messy in plain text)
sed -i 's/.*\r//' $OUT

echo
echo "HPC: ...DLC finished"
echo "HPC: End time is $(date) $(date +%s)"
