"""
Handle generating Anipose calibration files
"""

import logging 
from datetime import datetime
from pathlib import Path
from datetimerange import DateTimeRange
import src.file_tools as file_tools

def to_dt(date_string: str, time: bool = False) -> datetime:
    match = "%m%d%Y"  # only date
    if time:
        match = "%m%d%Y%H%M%S"  # if the DT string contains a time as well
    return datetime.strptime(date_string, match)


def get_date_time(p_project_dir: Path) -> datetime:
    # name format B-4182023151132-0000

    mp4_files = [file for file in p_project_dir.glob('**/*.mp4') if file.name.count('-') >= 2] # Excludes the `calib-A` etc. calibration movies from the search
    if not mp4_files:
        raise ValueError("No valid .mp4 files found in the directory")
    
    mp4 = mp4_files[0] # First valid mp4 file, used to get datetime range
    mp4_name = mp4.name
    date_time_string = mp4_name.split('-')[1]

    return to_dt(date_time_string, True)


def get_calibration_type(p_calibration_target: Path, p_project_dir: Path):
    """Return the calibration type of the directory based on the calibration_target file

    Parameters
    ----------
    p_calibration_target : Path
        File path to the calibration_target.yml file
    p_project_dir : Path
        File path to the directory to be checked for fly vs board-based

    Returns
    -------
    String OR None
        Returns a string "board" or "fly" if the directory provided is board-based or fly-based calibration respectively. Returns None and gives a logging error to the user if the directory is not inside calibration_target or is not a child of a path in calibration_target.
    """
    calibration_target_config = file_tools.load_config(p_calibration_target)

    # all the file paths that use a board calibration
    board_paths = calibration_target_config['board']
    # all the file paths that use a fly calibration
    fly_paths = calibration_target_config['fly']

    # Checks if the list of paths exists, then if the project_dir is exactly any of the paths in calibration_target, then if project_dir is a child of any paths in project_dir
    if board_paths and any(str(p_project_dir) == path or Path(path) in p_project_dir.parents for path in board_paths):
        return "board"
    elif fly_paths and any(str(p_project_dir) == path or Path(path) in p_project_dir.parents for path in fly_paths):
        return "fly"
    else:
        return None


def get_anipose_calibration_files(p_calibration_target: Path, p_calibration_timeline: Path, p_project_dir: Path) -> list:
    p_calibration_files = ""

    # specifies which calibration to use based on the timestamp on filename
    calibration_timeline = file_tools.load_config(p_calibration_timeline)

    # gets the datetime string from filename
    project_date = get_date_time(p_project_dir)

    for path, daterange in calibration_timeline.items():
        start = daterange.split("-")[0].strip()  # Start datetime
        end = daterange.split("-")[1].strip()  # end datetime
        dt_start = to_dt(start)
        dt_end = to_dt(end)
        # Create a date range (this just starts and ends at midnight since the time doesn't matter)
        dt_daterange = DateTimeRange(dt_start, dt_end)
        if project_date in dt_daterange:  # determine if the project falls in the date range
            p_calibration_files = Path(path)
            break
    else:
        logging.error(
            f"The project date (`{project_date}`) of the directory `{p_project_dir}` does not fall into any date range in calibration_timeline: `{p_calibration_timeline}`")
        return

    output_files = []
    p_common_files = Path('./common_files')
    if p_calibration_files and p_calibration_files.exists():  # calibration file dir found
        calibration_type = get_calibration_type(
            p_calibration_target, p_project_dir)
        p_detection_pickle = next(
            p_calibration_files.glob('**/detections.pickle'))
        p_calibration_toml = next(
            p_calibration_files.glob('**/calibration.toml'))


        if calibration_type == 'board':
            # Board calibration needs both files
            output_files.append(p_detection_pickle)
            output_files.append(p_calibration_toml)
        elif calibration_type == 'fly':
            p_calib_movies = list(p_common_files.glob("*.mp4"))

            # Fly-based calibration only requires detections.pickle
            output_files.append(p_detection_pickle)
            # Fly-based requires calibration movies 
            output_files += p_calib_movies # merges the two lists together
        else:
            logging.error(
                f"Invalid calibration type or calibration type not specified in `{p_calibration_target}")
            return
    else:
        logging.error("No matching calibration directory for video files")
        return

    return output_files