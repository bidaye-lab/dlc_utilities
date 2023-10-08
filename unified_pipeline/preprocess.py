"""
preprocess.py: various preprocessing functions used to prepare data for anipose (from DLC output)
"""

from datetimerange import DateTimeRange
from datetime import datetime
import utils
import shutil
from pathlib import Path
import pandas as pd
__author__ = "Nico Spiller, Jacob Ryabinky"

import logging
import pickle
pickle.HIGHEST_PROTOCOL = 4


root = Path(r"\\mpfi.org\public\sb-lab\DLC_pipeline_Dummy\0_QualityCtrl")


def create_file_name(path: Path, root: Path) -> Path:
    """Create appropriate filename from a path for each data file in the format GenotypeFlynum-camName, e.g: for camA in the BPN dataset, for fly N0, filename: BPNN1-A

    Parameters
    ----------
    path : Path
        The path to the data file
    root : Path
        The path to the root directory

    Returns
    -------
    Path 
        Path with file name in the format GenotypeFlynum-camName
    """

    """
    Directory structure example:

    BallSystem_RawData \ <Genotype info> \ <-1+ Subdirectories> \ <N1, N2...Nx> \ <Ball, SS> \ <Video & DLC files>

    Camera name - directly from DLC generated file names
    Fly number - parent of parent of DLC file
    Genotype - Child of root
    """
    path_rel = path.relative_to(root)

    cam_name = str(path.name).split("-")[0]
    fly_num = str(path.parent.parent.name).strip()
    genotype = str(path_rel.parts[0]).strip().replace("-", "").replace("_", "")
    file_name = genotype + fly_num + "-" + cam_name
    return Path(file_name)


def to_dt(date_string: str, time: bool = False) -> datetime:
    match = "%m%d%Y"  # only date
    if time:
        match = "%m%d%Y%H%M%S"  # if the DT string contains a time as well
    return datetime.strptime(date_string, match)


def get_date_time(p_project_dir: Path) -> datetime:
    # the first mp4 found, used to get date range
    mp4 = next(p_project_dir.glob('**/*.mp4'))
    # name format B-4182023151132-0000
    mp4_name = mp4.name
    date_time_string = mp4_name.split('-')[1]

    return to_dt(date_time_string, True)


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
        return None


def get_anipose_calibration_files(p_calibration_target: Path, p_calibration_timeline: Path, p_project_dir: Path) -> list:
    p_calibration_files = ""

    # specifies which calibration to use based on the timestamp on filename
    calibration_timeline = utils.load_config(p_calibration_timeline)

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
            f"Calibration type not specified in `{p_calibration_target}`")
        return

    output_files = []
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
            # Fly-based calibration only requires detections.pickle
            output_files.append(p_detection_pickle)
        else:
            logging.error(
                f"Invalid calibration type or calibration type not specified in `{p_calibration_target}")
            return
    else:
        logging.error("No matching calibration directory for video files")
        return

    return output_files


def fix_point(df: pd.DataFrame, col_name: str, n: int = 1) -> pd.DataFrame:
    """Replace all values in a DataFrame corresponding to DLC CSV data with one value. 
    This is useful for a point that should stay fixed. Missing values are conserved. 
    Original file is overwritten.

    Parameters
    ----------
    df: DataFrame 
        Panda DataFrame representing CSV data 
    col_name : str, optional
        Name of the columns
    n : int, optional
        Replace values with nth entry. To replace with the mean of whole column, choose 0, by default 1

    Returns
    -------
    df : pd.DataFrame
        Full dataframe (representing DLC CSV) with specified points fixed
    """

    # select columns of interests and here only values
    c = df.loc[3:, df.loc[1, :] == col_name].astype(float)

    if n > 0:
        x = c.iloc[n-1, :]  # select value (python starts counting at 0)
    else:
        x = c.mean()  # calculate mean

    # replace all non-nan values with x
    c.where(c.isnull(), x, axis=1, inplace=True)
    logging.info(f"value in {col_name} replaced with {x.values}")

    df.loc[c.index, c.columns] = c  # merge back to full dataframe

    return df


def remove_cols(df: pd.DataFrame, start: str = "") -> pd.DataFrame:
    """Remove columns in a DEEPLABCUT CSV based on second rows (bodyparts).
        This is useful when certain joints are badly tracked.

    Parameters
    ----------
    df : pd.DataFrame
        Panda DataFrame representing CSV data 
    start : str, optional
        Remove column if name starts with given string, by default ""

    Returns
    -------
    DataFrame
        Full dataframe (representing DLC CSV) with columns removed
    """

    # filter columns based on beginning of name
    if start:
        # find cols with the particular start string
        cols = df.loc[:, df.loc[1, :].apply(
            lambda x: str(x).startswith(start))].columns
        df = df.drop(columns=cols)
        logging.info(
            ' removed {} columns starting with {}'.format(len(cols), start))

    return df


def clean_dfs(p_csv: Path) -> pd.DataFrame:
    """Run any functions that clean the raw data. Any new cleaning steps can be added here.

    Parameters
    ----------
    p_csv : Path
        path to a CSV file that will be processed.

    Returns
    -------
    pd.DataFrame
        Processed CSV as a DF
    """
    logging.info(f"Processing {p_csv.name}")
    csv_df = utils.load_csv_as_df(p_csv)

    # Fix points
    logging.info(" Running `Fix points` preprocessing...")
    # Columns which will have points fixed, add/remove to change which cols processed
    col_names = [
        'R-F-ThC', 'R-M-ThC', 'R-H-ThC',
        'L-F-ThC', 'L-M-ThC', 'L-H-ThC',
        'R-WH', 'L-WH',
        'Notum',
    ]
    n = 0  # Values will be replaced with the nth entry. To replace with the mean, use n=0
    for name in col_names:
        logging.info(f" Matching string {name}")
        csv_df = fix_point(csv_df, name, n)

    # Remove cols
    logging.info("Running `Remove cols` preprocessing...")
    camName = p_csv.name[0]  # Camera letter name
    start = ''
    # TODO: remove end from here and function, since unused
    if camName == 'B':
        logging.info("camName `B`, removing cols starting with `L-`")
        start = 'L-'  # Remove col if start of name matches string
    if camName == 'E':
        logging.info("camName `E`, removing cols starting with `R-`")
        start = 'R-'  # Remove col if start of name matches string
    csv_df = remove_cols(csv_df, start)

    return csv_df


def df2hdf(df: pd.DataFrame, csv_path: Path, write_path: Path, root: Path = root) -> None:
    """Convert pandas DF provided to hdf format and save with proper name format 

    Parameters
    ----------
    df : pd.DataFrame
        DF representing DLC data
    csv_path : Path
        Path to original CSV from which DF was generated
    write_path : Path
        Path to which HDF will be written
    root : Path, optional
        Root directory, by default root
    """
    # Create new file name
    try:
        # get filename from csv path in the form GenotypeFlynum-camName
        file_name = create_file_name(csv_path, root)
    except ValueError:
        logging.critical("Incorrect root.\nYour root path does not match with the parent directory provided, please make sure that you provided the correct root. \
        \nThe root should be the beginning of your parent directory path up to the folder containing raw data, e.g `\mpfi.org\public\sb-lab\BallSystem_RawData`\n")
        return -1

    hdf_name = file_name.with_suffix('.h5')

    # save to disk
    hdf_path = write_path / hdf_name
    logging.info(f"Writing to file {hdf_path}")
    df.to_hdf(hdf_path, key='df_with_missing', mode='w')


def traverse_dirs(directory_structure: dict, parent_dir: Path, path: Path = Path('')) -> None:
    """Traverse the directory dict structure and generate analagous file structure

    All directories are dicts but files are represented with the key 'files' and a list of either file names (with extension) or the full path to an existing file.
    If the full path is provided, then the existing file will be moved from that location to the location specified in the dictionary structure.

    Parameters
    ----------
    directory_structure : dict
        File structure represented as a dictionary. 
    parent_dir : Path
        Path to parent directory. The dictionary file structure will be generated such that path/<dict structure>
    path : Path, optional
        Used to call function recursively.
    """
    for parent, child in directory_structure.items():  # loop over the directory structure
        if isinstance(child, dict):  # dict is a directory, create dir and then call recursively
            newpath = (path / parent)
            if not newpath.exists():
                logging.info(f" Creating new directory {newpath}")
                newpath.mkdir()
                # recursively call to traverse all subdirs
                traverse_dirs(child, parent_dir, path=newpath)
            else:
                logging.warning(
                    f"Skipping creating {newpath} because it already exists")
        elif parent == 'filesmv' and child:  # move files in child list
            for file in child:
                if isinstance(file, Path):
                    filepath = path / file.name
                    if not filepath.exists():
                        logging.info(f"Moving file {file} to {filepath}")
                        # if file path entered, move the existing file here
                        file.rename(filepath)
                else:
                    logging.warning(
                        f"Skipping {file}, all files in `filesmv` should be paths")
        elif parent == 'filescp' and child:  # copy files in child list
            for file in child:
                if isinstance(file, tuple):  # (file, with name)
                    original_filepath = file[0]
                    new_name = file[1]
                    filepath = path / new_name
                    if not filepath.exists():
                        logging.info(
                            f"Copying file {original_filepath} to {filepath}")
                        shutil.copy(original_filepath, filepath)
                # If just path, then the file name will be the same as original
                elif isinstance(file, Path):
                    filepath = path / file.name
                    if not filepath.exists():
                        logging.info(f"Copying file {file} to {filepath}")
                        shutil.copy(file, filepath)
                else:
                    logging.warning(
                        f"Skipping {file}, all files in `filescp` should be paths")
        elif parent == 'filescv':  # convert files in child list
            for df, csv_path in child:
                # The DF should only be written to the Nx folder it was taken from,
                # check that DF original Nx folder matches the current path
                csv_nx = csv_path.parent.parent.name  # Nx folder for the original CSV
                current_nx_dir = path.parent.name  # Nx dir currently being traversed
                # Check that parent directory and Nx folder are the same
                if parent_dir in csv_path.parents and csv_nx == current_nx_dir:

                    df2hdf(df, csv_path, path, root)
        elif parent == 'filesmk' and child:  # Create the file if only the file name provided
            for file in child:
                filepath = path / file
                if not filepath.exists():
                    logging.info(f"Creating new file at: {filepath}")
                    # if only file name entered, create at location
                    filepath.touch()


def gen_anipose_files(parent_dir: Path, p_network_cfg: Path, p_calibration_target: Path, p_calibration_timeline: Path, preprocessed_dfs: list, p_gcam_dummy: Path, structure: dict = {}) -> None:
    """Generate the necessary anipose file structure given a parent path and a file structure

    Parameters
    ----------
    parent_dir : Path
        Parent directory. This is where anipose folder will be placed
    p_network_cfg: Path 
        File path to the config file containing DLC model paths
    p_calibration_target: Path
        File path to calibration target config file
    p_calibration_timeline: Path
        File path to calibration timeline config file
    preprocessed_dfs: list
        List of tuples in the form (processed_df, csv_path)
    p_gcam_dummy: Path
        filepath to the gcam dummy file
    structure : dict, optional
        The file structure represented as a dictionary, by default {}. If left blank, default will be used. The default will be the minimum required for anipose.

        Dictionary mirrors file structure with directories represented by other dictionaries and files represented by lists with three types of keys:\n
             1. `filesmv` - this key takes a list of Path objects and moves the files from the path provided to the new path specified in the dict structure
             2. `filescp` - this key takes a list of Path objects and copies the files from the path provided to the new path specified in the dict structure
             3. `filesmk` - this key takes a list of strings that specify the name and extension of a new file that will be created at the path specified in the dict structure
    """

    # Get anipose calib files based on configs set
    calibration_type = get_calibration_type(p_calibration_target, parent_dir)
    if calibration_type == 'fly':
        # anipose config file
        p_anipose_config = Path(r"./common_files/config_fly.toml")
    elif calibration_type == 'board':
        # anipose config file
        p_anipose_config = Path(r"./common_files/config_board.toml")
    else:
        logging.error(
            f"Invalid calibration type or calibration type not specified in {p_calibration_target}")
        return

    logging.info(f"Getting Anipose calibration files...")
    calibration_files = get_anipose_calibration_files(
        p_calibration_target, p_calibration_timeline, parent_dir)
    if not calibration_files:  # calib files could not be found
        logging.error("Calibration files not found")
        return

    # Generate `project` folder structure for anipose
    project = {}
    genotype = ""
    logging.info(f"Generating `project` folder structure...")
    for folder in parent_dir.glob('N*'):  # find all fly folders (N1-Nx)

        logging.info(f"Searching {folder.name} directory")
        csv_files = []
        ball_folder = parent_dir / folder / 'Ball'
        for file in ball_folder.glob('*.csv'):  # Find all .csv files
            if not genotype:
                # get genotype for G-cam dummy file
                genotype = utils.get_genotype(file, root)
            # only process the filtered CSVs
            if 'filtered' in file.name:  # TODO: change to check for model name and cam as well, i.e make sure that only grabbing files which match the currently set networks
                logging.info(f"Found filtered CSV file {file}")
                csv_files.append(file)
        # Create the gcam dummy file name by filling in the genotype and fly number
        gcam = (p_gcam_dummy, f"{genotype}{folder.name}-G.h5")
        # Structure for the anipose `project` folder
        project[folder.name] = {
            'pose-2d': {
                'filescv': preprocessed_dfs,  # will convert the DFs to HDF
                'filescp': [gcam]  # will copy the gcam file
            },
            'videos-raw': {}
        }

    # Get network set name
    cfg = utils.load_config(p_network_cfg)
    network_set_name = cfg['Ball']['name']  # network set for ball
    logging.info(f"Using network set name {network_set_name}")
    if not structure:
        logging.info("Using default anipose file structure")
        # Default file structure
        structure = {
            'anipose': {
                'Ball': {
                    f'{network_set_name}': {
                        # will copy calibration files
                        'calibration': {'filescp': calibration_files},
                        'project': project,  # N1-Nx
                        # Will copy the anipose config as `config.toml`
                        'filescp': [(p_anipose_config, 'config.toml')]
                    },
                },
                'SS': {},
            }
        }

    traverse_dirs(structure, parent_dir, parent_dir)


def run_preprocessing(videos: Path, p_networks: Path,
                      p_calibration_target=Path(
                          'common_files/calibration_target.yml'),
                      p_calibration_timeline=Path(
                          'common_files/calibration_timeline.yml'),
                      p_gcam_dummy=Path('common_files/GenotypeFly-G.h5')):
    """Runs preprocessing on all CSV files generated by DLC in provided path

    Parameters
    ----------
    videos : Path
        Path to folder containing videos (doesn't have to be direct parent)
    p_networks : Path
        Path to network config files for DLC
    p_calibration_target : Path, optional
        Path to the YML file which defines which folders require board- and 
        fly-based calibrations, by default Path('common_files/calibration_target.yml')
    p_calibration_timeline : Path, optional
        Path to the YML file which defines which calibration movie to use
        for which time range, by default Path('common_files/calibration_timeline.yml')
    p_gcam_dummy : Path, optional
        Path to the h5 file used as dummy for camera G,
        by default Path('common_files/GenotypeFly-G.h5')
    """
    # TODO: get network name from common files like everything else

    # find all the CSVs that DLC generated
    # Will contain a dictionary with the filepath: list of tuples in form (csv_df, p_csv)
    processed_dirs = {}
    for p_csv in videos.glob("**/*_filtered.csv"):  # get all filtered CSVs
        # The directory holding all data for that particular experiment, i.e parent of nx dir
        parent_dir = p_csv.parent.parent.parent

        # TODO: also check for cam name and model name

        # Fix points, remove columns
        csv_df = clean_dfs(p_csv)

        processed_csv = (csv_df, p_csv)
        if parent_dir in processed_dirs:
            # Append to list of processed CSVs under that parent directory
            processed_dirs[parent_dir].append(processed_csv)
        else:
            # Create list of processed CSVs under that parent directory
            processed_dirs[parent_dir] = [processed_csv]

    # Generate anipose file structure
    # check that all the files exist
    for p in [p_calibration_target, p_calibration_timeline, p_gcam_dummy]:
        if not p.exists():
            raise FileNotFoundError(f"{p} does not exist.")

    logging.info("Generating anipose files...")
    for parent_dir, processed_csvs in processed_dirs.items():
        if not gen_anipose_files(parent_dir, p_networks, p_calibration_target, p_calibration_timeline, processed_csvs, p_gcam_dummy):
            # TODO: gen_anipose_files needs to return somethng when it finishes (maybe directory where it was generated)
            logging.warning(f"Skipped anipose generation for {parent_dir}")
    print('Finished preprocessing...')
