"""
# Step 2/2 of the overall pipeline. 

Uses the Anaconda environment created for DeepLabCut

Note: Will skip running Anipose if it has 1. been run already for ALL commands below or 2. is missing critical files

## Steps
  1. Find all Anipose directories within given root
  1. Determine each project calibration type (board-based or fly-based)
  2. Run Anipose commands
    - Fly based: `anipose filter`, `anipose calibrate`, `anipose triangulate`, `anipose angles`
    - Board based: 'anipose filter', 'anipose triangulate', 'anipose angles'
"""

__author__ = "Jacob Ryabinky"

import logging
logger = logging.getLogger()
logger.debug("Logging works :)")

from pipeline.config import VIDEOS_PATH 

import subprocess
from pathlib import Path

from src.file_tools import find_nx_dirs
from src.calibration import get_calibration_type


def run_anipose_commands(wdir, p_calibration_target: Path, p_project_dir: Path):
    is_fly_based = get_calibration_type(p_calibration_target, p_project_dir) == "fly"

    if is_fly_based == None:
        logger.error(f"Could not find {p_project_dir} in calibration target: {p_calibration_target}")
        logger.warning("Defaulting to anipose commands WITHOUT `anipose calibrate` being run")

    commands = (['anipose filter', 'anipose calibrate', 'anipose triangulate', 'anipose angles'] if is_fly_based 
                else ['anipose filter', 'anipose triangulate', 'anipose angles'])

    for command in commands: # run all commands
        logger.info(f'Running {command}')
        process = subprocess.run(command.split(), cwd=wdir, check=False, capture_output=True)

        logger.info('STDERR:\n' + process.stderr.decode('UTF-8'))
        logger.info('STDOUT:\n' + process.stdout.decode('UTF-8'))

        if process.returncode != 0:
            logger.critical(f'Command {command} failed with return code {process.returncode}')
            break

def run(parent_dir: Path = VIDEOS_PATH) -> None:
    """Find all valid anipose projects and run anipose processing commands on that data.

    Parameters
    ----------
    parent_dir : Path
        Parent directory of the anipose project(s)
    """

    num_run = 0 # number of times anipose has been run (essentially number of dirs modified)
    nx_dirs = find_nx_dirs(parent_dir)
    for nxdir in nx_dirs: # run on all Nx dirs
        p_anipose = nxdir / 'anipose' 
        if not p_anipose.exists():
            logger.warning(f"Anipose directory does not exist, skipping {nxdir}")
            continue
        logger.info(f"Found anipose directory {p_anipose}")
        for p_n1 in p_anipose.glob('**/N1'):
            p_network = p_n1.parent.parent # anipose\Ball\<name of network set>\project\N1
            logger.info(f"Name of network set (directory): `{p_network.name}`")

            # check if anipose has been run
            p_pose_3d = p_n1 / 'pose-3d'
            p_pose_2d_filtered = p_n1 / 'pose-2d-filtered'
            p_angles = p_n1 / 'angles'

            if p_pose_3d.exists() and p_pose_2d_filtered.exists() and p_angles.exists():
                logger.info(f'All anipose generated files present, skipping {p_network}')
                continue

            # check if anipose directory is valid
            # TODO: put all dirs in a list and run with a loop to check if missing
            p_proj = p_network / 'project'
            p_cal= p_network / 'calibration'
            p_cfg = p_network / 'config.toml'
            if not (p_proj.exists() and p_cal.exists() and p_cfg.exists()):
                logger.info(f'Skipping {p_network}, invalid anipose file structure')
                continue


            p_common_files = Path(r'../common_files')
            p_calibration_target = p_common_files / 'calibration_target.yml'

            # run anipose commands
            logger.info(f'Changing directory to {p_network}')
            run_anipose_commands(p_network, p_calibration_target, parent_dir)
            num_run+=1
            logger.info(f'Finished running anipose in {p_network}')
    print(f"Finished running anipose in {num_run} projects...")

