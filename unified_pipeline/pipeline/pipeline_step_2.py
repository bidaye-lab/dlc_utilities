"""
# Step 2/2 of the overall pipeline.

Uses the Anaconda environment created for DeepLabCut

Note: Will skip running Anipose if it has 1. been run already for ALL N* folders in a condition
or 2. is missing critical files (project/, calibration/, config.toml).

## Steps
  1. Find all Anipose directories within given root
  2. Determine each project calibration type (board-based or fly-based)
  3. Run Anipose commands per condition
    - Fly based:   `anipose filter`, `anipose calibrate`, `anipose triangulate`, `anipose angles`
    - Board based: `anipose filter`, `anipose triangulate`, `anipose angles`
"""

__author__ = "Jacob Ryabinky"

import logging
import re
import subprocess
from pathlib import Path

logger = logging.getLogger()
logger.debug("Logging works :)")

from config import settings, COMMON_FILES
VIDEOS_PATH  = Path(settings.videos_path)

from src.file_tools import find_nx_dirs
from src.calibration import get_calibration_type


def run_anipose_commands(wdir: Path, p_calibration_target: Path, p_project_dir: Path) -> None:
    is_fly_based = get_calibration_type(p_calibration_target, p_project_dir) == "fly"

    if is_fly_based is None:
        logger.error(f"Could not find {p_project_dir} in calibration target: {p_calibration_target}")
        logger.warning("Defaulting to anipose commands WITHOUT `anipose calibrate` being run")

    commands = (
        ['anipose filter', 'anipose calibrate', 'anipose triangulate', 'anipose angles']
        if is_fly_based
        else ['anipose filter', 'anipose triangulate', 'anipose angles']
    )

    for command in commands:
        logger.info(f'Running {command}')
        process = subprocess.run(command.split(), cwd=wdir, check=False, capture_output=True)

        logger.info('STDERR:\n' + process.stderr.decode('UTF-8'))
        logger.info('STDOUT:\n' + process.stdout.decode('UTF-8'))

        if process.returncode != 0:
            logger.critical(f'Command {command} failed with return code {process.returncode}')
            break


def run(parent_dir: Path = VIDEOS_PATH) -> None:
    """Find all valid anipose projects and run anipose processing commands on that data.

    Iterates over condition directories (Ball, SS, Air, Amp) inside each anipose/ folder.
    Anipose is run once per condition; all N* fly folders are processed in that single run.
    A condition is skipped if ALL its N* folders already have pose-3d, pose-2d-filtered,
    and angles outputs.

    Parameters
    ----------
    parent_dir : Path
        Parent directory of the anipose project(s).
    """
    p_calibration_target = COMMON_FILES / 'calibration_target.yml'

    num_run = 0
    nx_dirs = find_nx_dirs(parent_dir)

    for nxdir in nx_dirs:
        p_anipose = nxdir / 'anipose'
        if not p_anipose.exists():
            logger.warning(f"Anipose directory does not exist, skipping {nxdir}")
            continue

        logger.info(f"Found anipose directory: {p_anipose}")

        # Iterate over condition directories (Ball, SS, Air, Amp) directly
        for p_condition in sorted(p_anipose.iterdir()):
            if not p_condition.is_dir():
                continue

            # Validate the anipose folder structure for this condition
            p_proj = p_condition / 'project'
            p_cal  = p_condition / 'calibration'
            p_cfg  = p_condition / 'config.toml'
            if not (p_proj.exists() and p_cal.exists() and p_cfg.exists()):
                logger.info(f'Skipping {p_condition.name}: missing project/, calibration/, or config.toml')
                continue

            # Find all N* fly folders inside project/
            nx_folders = sorted(
                d for d in p_proj.iterdir()
                if d.is_dir() and re.match(r'^N\d+$', d.name)
            )
            if not nx_folders:
                logger.warning(f'No N* folders found in {p_proj}, skipping')
                continue

            # Skip only if ALL N* folders already have complete anipose output
            already_done = all(
                (nx / 'pose-3d').exists()
                and (nx / 'pose-2d-filtered').exists()
                and (nx / 'angles').exists()
                for nx in nx_folders
            )
            if already_done:
                logger.info(f'Anipose output already complete for all flies in {p_condition.name}, skipping')
                continue

            logger.info(f'Running anipose for condition: {p_condition.name} '
                        f'({len(nx_folders)} fly folder(s): {[d.name for d in nx_folders]})')
            run_anipose_commands(p_condition, p_calibration_target, parent_dir)
            num_run += 1
            logger.info(f'Finished anipose for {p_condition.name}')

    print(f"Finished running anipose in {num_run} condition(s).")
