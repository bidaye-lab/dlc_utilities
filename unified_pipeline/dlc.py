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

   
    video_folders = []
    # Find all ball folders (Nx / Ball / Video files)
    for folder in videos_folders_path.glob('**/Ball'):
        video_folders.append(folder)
    
    for video_folder in video_folders:
        single_folder = []
        for video_file in video_folder.glob('*.mp4'):
            # Find all mp4 files within a single video folder
            single_folder.append(video_file)

        # Run DLC on each video file within the current video folder
        for i, video_file in enumerate(single_folder):
            logging.info(f"current movie {video_file.name}")
            cam_type = str(video_file.name)[0]
            if cam_type not in model_paths:
                logging.warning(f"Skipping video file, invalid camera type or movie file name {video_file.name}")
            elif cam_type == 'G':
                # Top-down view (Camera G) is ignored 
                continue
            else:
                logging.info(f"Camera: {cam_type}")
                logging.info(f"Model path: {model_paths[cam_type]}")
                logging.info("Video file path:", single_folder[i])
                config_path = Path(model_paths[cam_type]) / 'config.yaml' # path to the DLC config for that particular network
                logging.info(f"DLC Config path {config_path}\n")

                deeplabcut.analyze_videos(config_path, str(video_file), save_as_csv=True)
                deeplabcut.filterpredictions(config_path, str(video_file), save_as_csv=True)

                # deeplabcut.create_labeled_video(config_path, [str(single_folder[i])], videotype='.mp4', filtered=True)
    

