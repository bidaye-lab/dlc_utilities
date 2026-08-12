"""
# Step 1/2 of the overall pipeline.

Uses the Anaconda environment created for DeepLabCut

## Steps
  1. Run DLC on movies folder specified
  2. Run DLC post-processing (Data processing functions found in src.clean)
  3. Generate the required Anipose file structure
    - Convert DLC post-processed CSVs to HDF
    - Copy over HDFs, calibration files, and (if needed) calibration movies to Anipose directory with the correct sub-dirs
"""

__author__ = "Nico Spiller, Jacob Ryabinky"

import logging
import logging

logger = logging.getLogger(__name__)
# logger.setLevel(logger.INFO)
# logger.debug("Logging works :)")

import re
import pandas as pd
import shutil
from pathlib import Path
import glob as glob

# from pipeline.config import ROOT, VIDEOS_PATH, COMMON_FILES, SAVE_FINAL_CSV, SKIP_PREPROCESSING_FUNCTIONS
from config import settings

# TODO: these variables no longer needed the program should just directly use settings.setting_name etc.; same goes for other files that use settings
VIDEOS_PATH = Path(settings.videos_path)
COMMON_FILES = Path(settings.common_files)
SAVE_FINAL_CSV: bool = settings.save_final_csv
SKIP_PREPROCESSING_FUNCTIONS: bool = settings.skip_preprocessing_functions


from src.calibration import get_calibration_type, get_anipose_calibration_files
from src.clean import fix_point, replace_likelihood, remove_cols
from src.dlc import analyze_new
from src.file_tools import load_config, load_csv_as_df, get_genotype
from src.hdf import df2hdf

import pickle

pickle.HIGHEST_PROTOCOL = 4  # Important for compatibility


def _get_nx_and_condition(csv_path: Path):
    """Walk up csv_path's ancestors to find the N* folder and the condition subfolder
    directly beneath it (e.g. Ball, SS, Air, Amp).

    Returns (nx_name, condition_name), or (None, None) if not found.
    Structure asserted: .../<parent_dir>/<N*>/<condition>/.../<file>.csv
    """
    for i, ancestor in enumerate(csv_path.parents):
        if re.match(r"^N\d+$", ancestor.name):
            condition = csv_path.parents[i - 1].name if i > 0 else None
            return ancestor.name, condition
    return None, None


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
    logger.info(f"Processing {p_csv.name}")
    csv_df = load_csv_as_df(
        p_csv
    )  # Flat CSV (req'd for current method of preprocessing)

    if SKIP_PREPROCESSING_FUNCTIONS:
        # For debugging purposes, if you do not want to rerun these functions each time (to speed up this step), you can just skip over them
        return csv_df

    # Fix points
    logger.info(" Running `Fix points` preprocessing...")
    # Columns which will have points fixed, add/remove to change which cols processed
    col_names = [
        "R-F-ThC",
        "R-M-ThC",
        "R-H-ThC",
        "L-F-ThC",
        "L-M-ThC",
        "L-H-ThC",
        "R-WH",
        "L-WH",
        "Notum",
    ]
    n = 0  # Values will be replaced with the nth entry. To replace with the mean, use n=0
    csv_df = fix_point(csv_df, col_names, n)

    # Remove cols
    logger.info("Running `Remove cols` preprocessing...")
    camName = p_csv.name[0]  # Camera letter name
    start = ""
    # TODO: remove end from here and function, since unused
    if camName == "B":
        logger.info("camName `B`, removing cols starting with `L-`")
        start = "L-"  # Remove col if start of name matches string
    if camName == "E":
        logger.info("camName `E`, removing cols starting with `R-`")
        start = "R-"  # Remove col if start of name matches string
    if start:
        csv_df = remove_cols(csv_df, start)

    # Repalce 'likelihood' column values with 1.0
    csv_df = replace_likelihood(csv_df)

    return csv_df  # without file write


def traverse_dirs(
    directory_structure: dict, parent_dir: Path, path: Path = Path("")
) -> None:
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
    for (
        parent,
        child,
    ) in directory_structure.items():  # loop over the directory structure
        if isinstance(
            child, dict
        ):  # dict is a directory, create dir and then call recursively
            newpath = path / parent
            print(f"Traversing {newpath}")
            if not newpath.exists():
                logger.info(f" Creating new directory {newpath}")
                newpath.mkdir()
                # recursively call to traverse all subdirs
                traverse_dirs(child, parent_dir, path=newpath)
            else:
                logger.warning(f"Skipping creating {newpath} because it already exists")
        elif parent == "filesmv" and child:  # move files in child list
            for file in child:
                if isinstance(file, Path):
                    filepath = path / file.name
                    if not filepath.exists():
                        logger.info(f"Moving file {file} to {filepath}")
                        # if file path entered, move the existing file here
                        file.rename(filepath)
                else:
                    logger.warning(
                        f"Skipping {file}, all files in `filesmv` should be paths"
                    )
        elif parent == "filescp" and child:  # copy files in child list
            for file in child:
                if isinstance(file, tuple):  # (file, with name)
                    original_filepath = file[0]
                    new_name = file[1]
                    filepath = path / new_name
                    if not filepath.exists():
                        logger.info(f"Copying file {original_filepath} to {filepath}")
                        shutil.copy(original_filepath, filepath)
                # If just path, then the file name will be the same as original
                elif isinstance(file, Path):
                    filepath = path / file.name
                    if not filepath.exists():
                        logger.info(f"Copying file {file} to {filepath}")
                        shutil.copy(file, filepath)
                else:
                    logger.warning(
                        f"Skipping {file}, all files in `filescp` should be paths"
                    )
        elif parent == "filescv":  # convert files in child list
            for df, csv_path in child:
                # Route each CSV to the correct Nx/condition Anipose folder.
                # Walk up csv_path to find the N* folder and condition — works at any
                # subfolder depth below N*/<condition>.
                csv_nx, csv_condition = _get_nx_and_condition(csv_path)
                current_nx_dir = path.parent.name          # e.g. "N1"
                # anipose/<condition>/project/N1/pose-2d → parents[2].name == condition
                current_condition = path.parents[2].name   # e.g. "Ball"
                print(
                    f"Checking {csv_path.name}: nx={csv_nx}, condition={csv_condition}"
                )
                if (
                    csv_nx == current_nx_dir
                    and csv_condition == current_condition
                    and parent_dir in csv_path.parents
                ):
                    df2hdf(df, csv_path, path, parent_dir)
        elif (
            parent == "filesmk" and child
        ):  # Create the file if only the file name provided
            for file in child:
                filepath = path / file
                if not filepath.exists():
                    logger.info(f"Creating new file at: {filepath}")
                    # if only file name entered, create at location
                    filepath.touch()


def gen_anipose_files(
    parent_dir: Path,
    p_calibration_target: Path,
    p_calibration_timeline: Path,
    preprocessed_dfs: list,
    p_gcam_dummy: Path,
    structure: dict = {},
) -> None:
    """Generate the necessary anipose file structure given a parent path and a file structure

    Parameters
    ----------
    parent_dir : Path
        Parent directory. This is where anipose folder will be placed
    p_calibration_target: Path
        File path to calibration target config file
    p_calibration_timeline: Path
        File path to calibration timeline config file
    preprocessed_dfs: list
        List of tuples in the form (processed_df, csv_path)
    p_gcam_dummy: Path
        filepath to the gcam dummy file
    structure : dict, optional
        The file structure represented as a dictionary, by default {}.
    """

    # Get anipose calib files based on configs set
    calibration_type = get_calibration_type(p_calibration_target, parent_dir)
    if calibration_type == "fly":
        p_anipose_config = Path(r"../common_files/config_fly.toml")
    elif calibration_type == "board":
        p_anipose_config = Path(r"../common_files/config_board.toml")
    else:
        logger.error(
            f"Invalid calibration type or calibration type not specified in {p_calibration_target}"
        )
        return

    logger.info(f"Getting Anipose calibration files...")
    calibration_files = get_anipose_calibration_files(
        p_calibration_target, p_calibration_timeline, parent_dir
    )
    if not calibration_files:  # calib files could not be found
        logger.error("Calibration files not found")
        return

    # ---------- Ball ----------
    ball_project = {}
    genotype = ""
    logger.info(f"Generating `Ball` folder structure...")
    for folder in parent_dir.glob("N*"):  # find all fly folders (N1-Nx)
        logger.info(f"Searching {folder.name} directory")

        ball_folder = parent_dir / folder / "Ball"

        if not ball_folder.exists():
            logger.error(f"Ball folder {ball_folder} does not exist.")
            continue
        else:
            logger.info(f"Found Ball folder: {ball_folder}")
            ball_file = next(ball_folder.glob("**/*_filtered.csv"), None)
            if ball_file:
                genotype = get_genotype(ball_file, parent_dir)
                print(f"Genotype for {folder.name} is {genotype}")
            else:
                logger.error(f"Could not get genotype for {folder}.")
                logger.warning(f"Skipping this Nx directory!")
                continue

        # Create the gcam dummy file name by filling in the genotype and fly number
        try:
            gcam = (p_gcam_dummy, f"{genotype}-G.h5")
        except Exception:
            gcam = (p_gcam_dummy, f"{genotype}-G.h5")

        ball_project[ball_folder.parent.name] = {
            "pose-2d": {
                "filescv": preprocessed_dfs,  # will convert the DFs to HDF
                "filescp": [gcam],  # will copy the gcam file
            },
            "videos-raw": {},
        }

    # ---------- SS ----------
    SS_project = {}
    genotype = ""
    logger.info(f"Generating `SS` folder structure...")
    for folder in parent_dir.glob("N*"):  # find all fly folders (N1-Nx)
        logger.info(f"Searching {folder.name} directory")

        SS_folder = parent_dir / folder / "SS"

        if not SS_folder.exists():
            logger.error(f"SS folder {SS_folder} does not exist.")
            continue
        else:
            logger.info(f"Found SS folder: {SS_folder}")
            SS_file = next(SS_folder.glob("**/*_filtered.csv"), None)
            if SS_file:
                genotype = get_genotype(SS_file, parent_dir)
                print(f"Genotype for {folder.name} is {genotype}")
            else:
                logger.error(f"Could not get genotype for {folder}.")
                logger.warning(f"Skipping this Nx directory!")
                continue

        try:
            gcam = (p_gcam_dummy, f"{genotype}-G.h5")
        except Exception:
            gcam = (p_gcam_dummy, f"{genotype}-G.h5")

        SS_project[SS_folder.parent.name] = {
            "pose-2d": {
                "filescv": preprocessed_dfs,
                "filescp": [gcam],
            },
            "videos-raw": {},
        }

    # ---------- Air ----------
    Air_project = {}
    genotype = ""
    logger.info(f"Generating `Air` folder structure...")
    for folder in parent_dir.glob("N*"):  # find all fly folders (N1-Nx)
        logger.info(f"Searching {folder.name} directory")

        Air_folder = parent_dir / folder / "Air"

        if not Air_folder.exists():
            logger.error(f"Air folder {Air_folder} does not exist.")
            continue
        else:
            logger.info(f"Found Air folder: {Air_folder}")
            Air_file = next(Air_folder.glob("**/*_filtered.csv"), None)
            if Air_file:
                genotype = get_genotype(Air_file, parent_dir)
                print(f"Genotype for {folder.name} is {genotype}")
            else:
                logger.error(f"Could not get genotype for {folder}.")
                logger.warning(f"Skipping this Nx directory!")
                continue

        try:
            gcam = (p_gcam_dummy, f"{genotype}-G.h5")
        except Exception:
            gcam = (p_gcam_dummy, f"{genotype}-G.h5")

        Air_project[Air_folder.parent.name] = {
            "pose-2d": {
                "filescv": preprocessed_dfs,
                "filescp": [gcam],
            },
            "videos-raw": {},
        }

    # ---------- Amp ----------
    amp_project = {}
    genotype = ""
    logger.info(f"Generating `Amp` folder structure...")
    for folder in parent_dir.glob("N*"):  # find all fly folders (N1-Nx)
        logger.info(f"Searching {folder.name} directory")

        Amp_folder = parent_dir / folder / "Amp"

        if not Amp_folder.exists():
            logger.error(f"Amp folder {Amp_folder} does not exist.")
            continue
        else:
            logger.info(f"Found Amp folder: {Amp_folder}")
            Amp_file = next(Amp_folder.glob("**/*_filtered.csv"), None)
            if Amp_file:
                genotype = get_genotype(Amp_file, parent_dir)
                print(f"Genotype for {folder.name} is {genotype}")
            else:
                logger.error(f"Could not get genotype for {folder}.")
                logger.warning(f"Skipping this Nx directory!")
                continue

        try:
            gcam = (p_gcam_dummy, f"{genotype}-G.h5")
        except Exception:
            gcam = (p_gcam_dummy, f"{genotype}-G.h5")

        amp_project[Amp_folder.parent.name] = {
            "pose-2d": {
                "filescv": preprocessed_dfs,
                "filescp": [gcam],
            },
            "videos-raw": {},
        }

    # ---------- Default structure ----------
    if not structure:
        logger.info("Using default anipose file structure")
        structure = {
            "anipose": {
                "Ball": {
                    "calibration": {"filescp": calibration_files},
                    "project": ball_project,  # N1-Nx
                    "filescp": [(p_anipose_config, "config.toml")],
                },
                "SS": {
                    "calibration": {"filescp": calibration_files},
                    "project": SS_project,  # N1-Nx
                    "filescp": [(p_anipose_config, "config.toml")],
                },
                "Air": {
                    "calibration": {"filescp": calibration_files},
                    "project": Air_project,  # N1-Nx
                    "filescp": [(p_anipose_config, "config.toml")],
                },
                "Amp": {
                    "calibration": {"filescp": calibration_files},
                    "project": amp_project,  # N1-Nx
                    "filescp": [(p_anipose_config, "config.toml")],
                },
            }
        }

    traverse_dirs(structure, parent_dir, parent_dir)

    return True


def run_preprocessing(
    videos: Path = VIDEOS_PATH,
    p_calibration_target=COMMON_FILES / Path("calibration_target.yml"),
    p_calibration_timeline=COMMON_FILES / Path("calibration_timeline.yml"),
    p_gcam_dummy=COMMON_FILES / Path("GenotypeFly-G.h5"),
):
    """Runs preprocessing on all CSV files generated by DLC in provided path. This function will find ALL CSV files matching the pattern *_filtered.csv
    Thus, for any DLC generated output, the corresponding Anipose preprocessing will be run (any preprocessing on the data as well as the Anipose folder structure)
    The subfunction, traverse_dirs, that generates the file structure will check for duplicate dirs, so if an Anipose folder already exists, generation will be skipped.

    Parameters
    ----------
    videos : Path
        Path to folder containing videos (doesn't have to be direct parent)
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

    # find all the CSVs that DLC generated
    # Will contain a dictionary with the filepath: list of tuples in form (csv_df, p_csv)

    if SAVE_FINAL_CSV:
        logger.warning(
            "SAVE_FINAL_CSV Is enabled. This will save final preprocessed data to a csv with a name that ends in _preprocessed.\
                        Keep in mind this will make the pipeline significantly slower, as there will be dozens of file writes.\
                        Only enable if intended and typically for debugging purposes."
        )

    processed_dirs = {}
    for p_csv in videos.glob("**/*_filtered.csv"):  # get all filtered CSVs
        if "summary_videos" in p_csv.parts:
            continue

        # Walk up to find the N* folder; its parent is the experiment parent_dir.
        # Handles CSVs at any subfolder depth below N*/<condition>/.
        nx_folder = next(
            (a for a in p_csv.parents if re.match(r"^N\d+$", a.name)), None
        )
        if nx_folder is None:
            logger.warning(f"Skipping {p_csv}: no N* folder found in path")
            continue
        parent_dir: Path = nx_folder.parent
        if not parent_dir.exists():
            logger.error(
                f"Could not find the parent directory of {p_csv}. Check that the folder structure is correct"
            )
            continue

        # TODO: also check for cam name and model name

        # Fix points, remove columns
        csv_df = clean_dfs(p_csv)

        if SAVE_FINAL_CSV:
            # If config varialbe set, then save the preprocessed data to a CSV for examination
            csv_name = p_csv.stem  # name of the csv without extension
            preprocessed_name = p_csv + "_preprocessed"
            preprocessed_csv_path = p_csv.with_name(preprocessed_name).with_suffix(
                ".csv"
            )
            logger.info(f"Saving final preprocessed data to {preprocessed_csv_path}")
            csv_df.to_csv(preprocessed_csv_path)

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

    logger.info("Generating anipose files...")

    for parent_dir, processed_csvs in processed_dirs.items():

        ANIPOSE_DIRECTORY: Path = parent_dir / "anipose"
        if ANIPOSE_DIRECTORY.exists():
            logger.warning(
                f"Skipping {ANIPOSE_DIRECTORY} generation because it already exists. Please delete any old `anipose` directories to have them regenerated."
            )
            continue
        if not gen_anipose_files(
            parent_dir,
            p_calibration_target,
            p_calibration_timeline,
            processed_csvs,
            p_gcam_dummy,
        ):
            # TODO: gen_anipose_files needs to return somethng when it finishes (maybe directory where it was generated)
            logger.warning(f"Skipped anipose generation for {parent_dir}")
    print("Finished preprocessing...")
