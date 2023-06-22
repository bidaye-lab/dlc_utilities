"""
anipose.py: Run Anipose commands on DLC predictions to generate Anipose predictions
"""

__author__ = "Jacob Ryabinky"

import os
import subprocess
from pathlib import Path
import utils

def run_anipose_commands():
    commands = ['anipose filter', 'anipose triangulate', 'anipose angles']    
    for command in commands:
        print(f'[INFO] Running {command}')
        process = subprocess.run(command.split(), check=True)
        if process.returncode != 0:
            print(f'[ERROR] Command {command} failed with return code {process.returncode}')
            break

# TODO: Only run if anipose has not been run on it before
def run(parent_dir: Path) -> None:
    nx_dirs = utils.find_nx_dirs(parent_dir)
    for nxdir in nx_dirs:
        p_anipose = nxdir / 'anipose' 
        for p_n1 in p_anipose.glob('**/N1'):
            p_network = p_n1.parent.parent # anipose\Ball\<name of network set>\project\N1

            # check if anipose has been run
            p_pose_3d = p_n1 / 'pose-3d'
            p_pose_2d_filtered = p_n1 / 'pose-2d-filtered'
            p_angles = p_n1 / 'angles'

            if p_pose_3d.exists() and p_pose_2d_filtered.exists() and p_angles.exists():
                print(f'[INFO] All anipose generated files present, skipping {p_network}')
                continue

            # check if anipose directory is valid
            p_proj = p_network / 'project'
            p_cal= p_network / 'calibration'
            p_cfg = p_network / 'config.toml'
            if not (p_proj.exists() and p_cal.exists() and p_cfg.exists()):
                print(f'[INFO] Skipping {p_network}, invalid anipose file structure')
                continue

            # run anipose commands
            print(f'[INFO] Changing directory to {p_network}')
            os.chdir(p_network)
            run_anipose_commands()
            print(f'[INFO] Finished running anipose in {p_network}')

# path = Path(r'C:\Users\ryabinkyj\Documents\testanalyze\RawData\BIN-1')
# run(path)