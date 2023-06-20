"""
anipose.py: Run Anipose commands on DLC predictions to generate Anipose predictions
"""

__author__ = "Jacob Ryabinky"

import os
import subprocess
from pathlib import Path

def run_anipose_commands():
    commands = ['anipose filter', 'anipose triangulate', 'anipose angles']    
    for command in commands:
        print(f'[INFO] Running {command}')
        process = subprocess.run(command.split(), check=True)
        if process.returncode != 0:
            print(f'Command {command} failed with return code {process.returncode}')
            break

# TODO: Only run if anipose has not been run on it before
def run(parent_dir: Path) -> None:
    anipose_dirs = parent_dir.glob("**/anipose")
    for anipose_dir in anipose_dirs:
        print(f'[INFO] Changing to anipose directory to {anipose_dir}')
        os.chdir(anipose_dir)
        run_anipose_commands()
        print(f'[INFO] Finished running anipose')

path = Path(r'C:\Users\ryabinkyj\Documents\testanalyze\RawData\BIN-1')
run(path)