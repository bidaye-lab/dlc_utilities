"""
dlc.py: Run DLC commands on raw data and generate DLC predictions
"""

import logging
import deeplabcut
import glob as glob
from pathlib import Path
import utils 

# DLC Generation
def analyze_new(videos_folders_path: Path, cfg_path: Path) -> None:
    """Run appropriate model with DLC on each video

    Parameters
    ----------
    videos_folders_path : Path
        File path to genotype directory with experiment videos
    
    cfg_path : Path
        File path to the config file containing model paths
    """

    cfg = utils.load_config(cfg_path)
    model_paths = cfg['Ball'] # network_local is dev

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
            config_path = Path(model_paths[cam_type]) / 'config.yaml'
            if not config_path.is_file():
                logging.info('Skipping video file: config file does not exist')

            #TODO: Add checks that DLC hasn't been run in a folder (with that particular network set) before running DLC
            # get model name
            model_folder = config_path.parent
            model_csv = next(model_folder.glob('evaluation-results/iteration-*/*/*-results.csv'))
            model_name = model_csv.name.replace('-results.csv', '')
            # check if video already has been analyzed with given model
            output = video_file.parent / f'{video_file.stem}{model_name}_filtered.csv'
            if output.is_file():
                logging.info('Skipping video file: *_filtered.cvs file already exists')
                continue

            # additional logging
            logging.info(f"Camera: {cam_type}")
            logging.info(f"DLC Config path: {config_path}")
            logging.info(f"Model path: {model_paths[cam_type]}")
            logging.info(f"Video file path: {video_file}")

            # run DLC
            deeplabcut.analyze_videos(config_path, str(video_file), save_as_csv=True)
            deeplabcut.filterpredictions(config_path, str(video_file), save_as_csv=True)