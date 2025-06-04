"""
Run the DLC API on raw videos to analyze videos and generate tracking points
"""

import logging
from pathlib import Path
import deeplabcut
import src.file_tools as file_tools

# from pipeline.config import VIDEOS_PATH
from src.file_tools import load_config

from config import settings

VIDEOS_PATH = Path(settings.videos_path)


# DLC Generation
def analyze_new(
    videos_folders_path: Path = VIDEOS_PATH,
    network_sets_path: Path = Path("../common_files/DLC_network_sets.yml"),
) -> None:
    """Run appropriate model with DLC on each video

    Parameters
    ----------
    videos_folders_path : Path
        File path to genotype directory with experiment videos

    network_sets_path : Path
        File path to the config file containing model paths
    """

    network_sets = file_tools.load_config(network_sets_path)
    model_paths_ball = network_sets["Ball"]
    model_paths_SS = network_sets[
        "SS"
    ]  ## note: add more categories here if new networks for new contexts are added; eg: amputated, decap etc.

    # all folders to analyze (Nx / Ball / Video files)
    logging.info(f"Searching through {videos_folders_path}")

    ball_video_folders = [
        *videos_folders_path.glob("**/N*/Ball")
    ]  ## looks for 'Ball' subfolder insiede N* folders
    SS_video_folders = [
        *videos_folders_path.glob("**/N*/SS")
    ]  ## looks for 'SS' subfolder insiede N* folders

    logging.info(f"Found {len(ball_video_folders)} Ball folders")
    logging.info(f"Found {len(SS_video_folders)} SS folders")

    if len(ball_video_folders) == 0:
        print("No Ball video folders found, skipping analysis.")
        logging.warning("No Ball video folders found, skipping analysis.")

    else:
        # cycle through all video folders
        for video_folder in ball_video_folders:
            print()

            # all mp4 files
            video_files = [*video_folder.glob("*.mp4")]
            logging.info(f"Found {len(video_files)} MP4 files")

            # Run DLC on each video file within the current video folder
            for video_file in video_files:

                logging.info(f"Analyzing movie: {video_file.name}")

                # check if camera model is defined in `model_paths_ball``
                cam_type = video_file.name.split("-")[
                    0
                ]  # string before first '-' is camera name
                try:
                    p = model_paths_ball[cam_type]
                    if not p:  # if model is defined but path empty
                        logging.info(
                            f"Skipping video file: model path empty for Camera {cam_type}"
                        )
                        continue
                except KeyError:  # if model is not defined
                    logging.warning(
                        f"Skipping video file:  model path not defined for Camera {cam_type}"
                    )
                    continue

                # path to the DLC config for that particular network
                model_config_path = Path(model_paths_ball[cam_type]) / "config.yaml"
                if not model_config_path.is_file():
                    logging.warning(
                        f"Skipping video file: config file does not exist at {model_config_path}"
                    )
                    continue

                # determine model name
                model_config = file_tools.load_config(
                    model_config_path
                )  # read dlc cfg to get `iteration`
                n_iteration = model_config["iteration"]
                model_folder = (
                    model_config_path.parent
                    / f"evaluation-results/iteration-{n_iteration}/"
                )
                csvs = [
                    *model_folder.glob("*/*-results.csv")
                ]  # this should only find one CSV file
                if len(csvs) != 1:
                    logging.warning("Could not determine model name, skipping check ")
                else:
                    # get model name from CSV name
                    model_csv = csvs[0]
                    model_name = model_csv.name.replace("-results.csv", "")

                    # check if video already has been analyzed with given model
                    output = (
                        video_file.parent
                        / f"{video_file.stem}{model_name}_filtered.csv"
                    )
                    if output.is_file():
                        logging.info(
                            "Skipping video file: *_filtered.cvs file already exists"
                        )
                        continue

                # additional logging
                logging.info(f"Camera: {cam_type}")
                logging.info(f"DLC Config path: {model_config_path}")
                logging.info(f"Model path: {model_paths_ball[cam_type]}")
                logging.info(f"Video file path: {video_file}")

                # run DLC
                deeplabcut.analyze_videos(
                    model_config_path, str(video_file), save_as_csv=True
                )
                deeplabcut.filterpredictions(
                    model_config_path, str(video_file), save_as_csv=True
                )

    if len(SS_video_folders) == 0:
        print("No SS video folders found, skipping analysis.")
        logging.warning("No SS video folders found, skipping analysis.")
    else:
        # cycle through all video folders
        for video_folder in SS_video_folders:
            print()

            # all mp4 files
            video_files = [*video_folder.glob("*.mp4")]
            logging.info(f"Found {len(video_files)} MP4 files")

            # Run DLC on each video file within the current video folder
            for video_file in video_files:

                logging.info(f"Analyzing movie: {video_file.name}")

                # check if camera model is defined in `model_paths_SS``
                cam_type = video_file.name.split("-")[
                    0
                ]  # string before first '-' is camera name
                try:
                    p = model_paths_SS[cam_type]
                    if not p:  # if model is defined but path empty
                        logging.info(
                            f"Skipping video file: model path empty for Camera {cam_type}"
                        )
                        continue
                except KeyError:  # if model is not defined
                    logging.warning(
                        f"Skipping video file:  model path not defined for Camera {cam_type}"
                    )
                    continue

                # path to the DLC config for that particular network
                model_config_path = Path(model_paths_SS[cam_type]) / "config.yaml"
                if not model_config_path.is_file():
                    logging.warning(
                        f"Skipping video file: config file does not exist at {model_config_path}"
                    )
                    continue

                # determine model name
                model_config = file_tools.load_config(
                    model_config_path
                )  # read dlc cfg to get `iteration`
                n_iteration = model_config["iteration"]
                model_folder = (
                    model_config_path.parent
                    / f"evaluation-results/iteration-{n_iteration}/"
                )
                csvs = [
                    *model_folder.glob("*/*-results.csv")
                ]  # this should only find one CSV file
                if len(csvs) != 1:
                    logging.warning("Could not determine model name, skipping check ")
                else:
                    # get model name from CSV name
                    model_csv = csvs[0]
                    model_name = model_csv.name.replace("-results.csv", "")

                    # check if video already has been analyzed with given model
                    output = (
                        video_file.parent
                        / f"{video_file.stem}{model_name}_filtered.csv"
                    )
                    if output.is_file():
                        logging.info(
                            "Skipping video file: *_filtered.cvs file already exists"
                        )
                        continue

                # additional logging
                logging.info(f"Camera: {cam_type}")
                logging.info(f"DLC Config path: {model_config_path}")
                logging.info(f"Model path: {model_paths_SS[cam_type]}")
                logging.info(f"Video file path: {video_file}")

                # run DLC
                deeplabcut.analyze_videos(
                    model_config_path, str(video_file), save_as_csv=True
                )
                deeplabcut.filterpredictions(
                    model_config_path, str(video_file), save_as_csv=True
                )
