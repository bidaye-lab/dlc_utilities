"""
anipose.py: Run Anipose commands on DLC predictions to generate Anipose predictions
"""

__author__ = "Jacob Ryabinky"

import logging
import subprocess
from pathlib import Path
import utils

# ! This function is the exact same as the one in preprocess.py; we can decide on how to organize these functions later
def get_calibration_type(p_calibration_target: Path, p_project_dir: Path):
    calibration_target_config = utils.load_config(p_calibration_target)

    # all the file paths that use a board calibration
    board_paths = calibration_target_config['board']
    # all the file paths that use a fly calibration
    fly_paths = calibration_target_config['fly']

    if board_paths and any(str(p_project_dir) == path or Path(path) in p_project_dir.parents for path in board_paths):
        return "board"
    elif fly_paths and any(str(p_project_dir) == path or Path(path) in p_project_dir.parents for path in fly_paths):
        return "fly"
    else:
        logging.error(f"Could not find {p_project_dir} in calibration target: {p_calibration_target}")
        logging.warning("Defaulting to anipose commands WITHOUT `anipose calibrate` being run")
        return None


def run_anipose_commands(wdir, p_calibration_target: Path, p_project_dir: Path):
    is_fly_based = get_calibration_type(p_calibration_target, p_project_dir) == "fly"

    commands = (['anipose filter', 'anipose calibrate', 'anipose triangulate', 'anipose angles'] if is_fly_based 
                else ['anipose filter', 'anipose calibrate', 'anipose triangulate', 'anipose angles'])

    for command in commands: # run all commands
        logging.info(f'Running {command}')
        process = subprocess.run(command.split(), cwd=wdir, check=False, capture_output=True)

        logging.info('STDERR:\n' + process.stderr.decode('UTF-8'))
        logging.info('STDOUT:\n' + process.stdout.decode('UTF-8'))

        if process.returncode != 0:
            logging.critical(f'Command {command} failed with return code {process.returncode}')
            break

def run(parent_dir: Path) -> None:
    """Find all valid anipose projects and run anipose processing commands on that data.

    Parameters
    ----------
    parent_dir : Path
        Parent directory of the anipose project(s)
    """

    num_run = 0 # number of times anipose has been run (essentially number of dirs modified)
    nx_dirs = utils.find_nx_dirs(parent_dir)
    for nxdir in nx_dirs: # run on all Nx dirs
        p_anipose = nxdir / 'anipose' 
        logging.info(f"Found anipose directory {p_anipose}")
        for p_n1 in p_anipose.glob('**/N1'):
            p_network = p_n1.parent.parent # anipose\Ball\<name of network set>\project\N1
            logging.info(f"Name of network set (directory): `{p_network.name}`")

            # check if anipose has been run
            p_pose_3d = p_n1 / 'pose-3d'
            p_pose_2d_filtered = p_n1 / 'pose-2d-filtered'
            p_angles = p_n1 / 'angles'

            if p_pose_3d.exists() and p_pose_2d_filtered.exists() and p_angles.exists():
                logging.info(f'All anipose generated files present, skipping {p_network}')
                continue

            # check if anipose directory is valid
            # TODO: put all dirs in a list and run with a loop to check if missing
            p_proj = p_network / 'project'
            p_cal= p_network / 'calibration'
            p_cfg = p_network / 'config.toml'
            if not (p_proj.exists() and p_cal.exists() and p_cfg.exists()):
                logging.info(f'Skipping {p_network}, invalid anipose file structure')
                continue


            p_common_files = Path(r'./common_files')
            p_calibration_target = p_common_files / 'calibration_target.yml'

            # run anipose commands
            logging.info(f'Changing directory to {p_network}')
            run_anipose_commands(p_network, p_calibration_target, parent_dir)
            num_run+=1
            logging.info(f'Finished running anipose in {p_network}')
    print(f"Finished running anipose in {num_run} projects...")