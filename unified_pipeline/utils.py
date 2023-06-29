"""
utils.py: Utility, helper functions for DLC/Anipose pipeline
"""

__author__ = "Jacob Ryabinky"

import yaml
from pathlib import Path
import shutil
import pandas as pd
from datetime import datetime
from datetimerange import DateTimeRange


def load_config(path: str):
    """Load config yml as dict.

    Parameters
    ----------
    path: str
        Path to config yml file

    Returns
    -------
    config: dict
        dictionary 
    """

    with open(path, 'r') as f:
        cfg = yaml.safe_load(f)


    return cfg

def load_csv_as_df(csv: Path) -> pd.DataFrame:
    return pd.read_csv(csv, header=None)

def get_csvs(path: Path) -> list:
    csv_paths = []
    for csv in path.glob("**/*.csv"):
        csv_paths.append(csv)
    return csv_paths

def backup_file(path: Path) -> None:
    backup = Path(str(path) + '_backup')
    path.replace(backup) 
    print(f'[INFO] backup file saved to {backup}')

def find_nx_dirs(parent_dir: Path) -> list:
    dirs = []
    for n1 in parent_dir.glob('**/N1'):
        parent = n1.parent
        if parent.name != 'project':
            dirs.append(parent)
    return dirs

def create_file_path(path: Path, root: Path) -> Path:
    """Create appropriate filename from a path for each data file in the format GenotypeFlynum-camName, e.g: for camA in the BPN dataset, for fly N1, filename: BPNN1-A

    Parameters
    ----------
    path : Path
        The path to the data file

    Returns
    -------
    Path 
        Path with file name in the format GenotypeFlynum-camName
    """
    
    """
    Directory structure example:

    BallSystem_RawData \ <Genotype info> \ <0+ Subdirectories> \ <N1, N2...Nx> \ <Ball, SS> \ <Video & DLC files>

    Camera name - directly from DLC generated file names
    Fly number - parent of parent of DLC file
    Genotype - Child of root
    """
    path_rel = path.relative_to(root)


    cam_name = str(path.name)[0]
    fly_num = str(path.parent.parent.name).strip()
    genotype = str(path_rel.parts[0]).strip().replace("-", "").replace("_", "")
    file_name = genotype + fly_num + "-" + cam_name
    return path.with_name(file_name).with_suffix(path.suffix)


def to_dt(date_string: str, time: bool = False) -> datetime:
    match="%m%d%Y"
    if time:
        match = "%m%d%Y%H%M%S"
    return datetime.strptime(date_string, match)

def get_date_time(p_project_dir: Path) -> datetime:
    mp4 = next(p_project_dir.glob('**/*.mp4')) # the first mp4 found, used to get date range
    # name format B-04182023151131-0000
    mp4_name = mp4.name 
    date_time_string= mp4_name.split('-')[1]

    return to_dt(date_time_string, True) 

def get_calibration_type(p_calibration_target: Path, p_project_dir: Path):
    calibration_target_config = load_config(p_calibration_target)

    board_paths = calibration_target_config['board'] # all the file paths that use a board calibration
    fly_paths = calibration_target_config['fly'] # all the file paths that use a fly calibration

    if any(str(p_project_dir) == path or Path(path) in p_project_dir.parents  for path in board_paths):
        return "board"
    elif any(str(p_project_dir) == path or Path(path) in p_project_dir.parents  for path in fly_paths):
        return "fly"
    else:
        return None

def get_anipose_calibration_files(p_calibration_target: Path, p_calib_timeline: Path, p_project_dir: Path) -> list:
    p_calibration_files = ""
   
    calibration_timeline = load_config(p_calib_timeline)

   
    project_date = get_date_time(p_project_dir)

    for path, daterange in calibration_timeline.items():
        start = daterange.split("-")[0].strip()
        end =  daterange.split("-")[1].strip()
        dt_start = to_dt(start)
        dt_end = to_dt(end)
        dt_daterange = DateTimeRange(dt_start, dt_end)
        if project_date in dt_daterange: # determine if the project falls in the date range
            p_calibration_files = Path(path)

    output_files=[]
    if p_calibration_files: # calibration file dir found
        calibration_type = get_calibration_type(p_calibration_target, p_project_dir)
        p_detection_pickle = next(p_calibration_files.glob('**/detections.pickle'))
        p_calibration_toml = next(p_calibration_files.glob('**/calibration.toml')) 
        if calibration_type == 'board':
            output_files.append(p_detection_pickle)
            output_files.append(p_calibration_toml)
        elif calibration_type == 'fly':
            output_files.append(p_detection_pickle)
        else:
            print(f"[ERROR] Invalid calibration type or calibration type not specified in `{p_calibration_target}")
    else:
        print("[ERROR] No matching calibration directory for video files")

    return output_files
