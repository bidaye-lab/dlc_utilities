"""
dlc.py: Run DLC commands on raw data and generate DLC predictions
"""

import logging
import deeplabcut
import glob as glob
from pathlib import Path
import utils 

# DLC Generation
def analyze_new(videos_folders_path: Path, network_sets_path: Path) -> None:
    """Run appropriate model with DLC on each video

    Parameters
    ----------
    videos_folders_path : Path
        File path to genotype directory with experiment videos
    
    network_sets_path : Path
        File path to the config file containing model paths
    """

    network_sets = utils.load_config(network_sets_path)
    model_paths = network_sets['Ball'] # network_local is dev

    """ network_local: 

    model_paths = {
        'A': r"C:\\Users\ryabinkyj\Documents\testanalyze\DLCModels\camA_augmented-BidayeLab-2023-01-18",
        'B':'C:\\Users\\ryabinkyj\\Documents\\testanalyze\\DLCModels\\3cam_BEH-BidayeLab-2022-09-16',
        'C':'C:\\DLC\\3D_8cam_vid\\camC_FS34_RN101-BidayeLab-2022-10-01',
        'D':r"C:\\Users\ryabinkyj\Documents\testanalyze\DLCModels\camD_FS34_RN101-BidayeLab-2022-09-20",
        'E':r"C:\\Users\ryabinkyj\Documents\testanalyze\DLCModels\3cam_BEH-BidayeLab-2022-09-16",
        'F':'C:\\DLC\\3D_8cam_vid\\camF_FS34_RN101-BidayeLab-2022-10-01',
        'G': None, # Top-down view ignored, no model
        'H':r"C:\\Users\ryabinkyj\Documents\testanalyze\DLCModels\3cam_BEH-BidayeLab-2022-09-16"
    }
    """

    # all folders to analyze (Nx / Ball / Video files)
    logging.info(f"Searching through {videos_folders_path}")
    video_folders = [ *videos_folders_path.glob('**/N*/Ball') ]
    logging.info(f"Found {len(video_folders)} Ball folders")

    # cycle through all video folders
    for video_folder in video_folders:
        print()

        # all mp4 files
        video_files = [ *video_folder.glob('*.mp4') ] 
        logging.info(f"Found {len(video_files)} MP4 files")

        # Run DLC on each video file within the current video folder
        for video_file in video_files:

            logging.info(f"Analyzing movie: {video_file.name}")

            # string before first '-' is camera name
            cam_type = video_file.name.split('-')[0]
            if cam_type not in model_paths:  # check if model is defined
                logging.warning(f"Skipping video file: invalid camera type or movie file name")
                continue
            elif cam_type == 'G': # Top-down view (Camera G) is ignored 
                logging.info("Skipping video file: Camera G") 
                continue

            # path to the DLC config for that particular network
            model_config_path = Path(model_paths[cam_type]) / 'config.yaml'
            if not model_config_path.is_file():
                logging.info('Skipping video file: config file does not exist')

            # determine model name
            model_config = utils.load_config(model_config_path) # read dlc cfg to get `iteration`
            n_iteration = model_config['iteration']
            model_folder = model_config_path.parent / f'evaluation-results/iteration-{n_iteration}/'
            csvs = [ *model_folder.glob('*/*-results.csv')] # this should only find one CSV file
            if len(csvs) != 1:
                logging.warning('Could not determine model name, skipping check ')
            else:
                # get model name from CSV name
                model_csv = csvs[0]
                model_name = model_csv.name.replace('-results.csv', '')

                # check if video already has been analyzed with given model
                output = video_file.parent / f'{video_file.stem}{model_name}_filtered.csv'
                if output.is_file():
                    logging.info('Skipping video file: *_filtered.cvs file already exists')
                    continue

            # additional logging
            logging.info(f"Camera: {cam_type}")
            logging.info(f"DLC Config path: {model_config_path}")
            logging.info(f"Model path: {model_paths[cam_type]}")
            logging.info(f"Video file path: {video_file}")

            # run DLC
            deeplabcut.analyze_videos(model_config_path, str(video_file), save_as_csv=True)
            deeplabcut.filterpredictions(model_config_path, str(video_file), save_as_csv=True)