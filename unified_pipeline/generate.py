import deeplabcut
import pandas as pd
import os
import glob as glob
from pathlib import Path
from utils import load_config

def analyze_new(videos_folders_path: Path):
    """Run approTODO: unhardcode into config file priate DLC models on videos in a given directory

    Parameters
    ----------
    videos_folders_path : Path
        File path to genotype directory with experiment videos
    """
    # TODO: unhardcode into config file 



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
   
    video_folders = []
    for folder in videos_folders_path.glob('*/Ball'):
        video_folders.append(folder)
    
    for video_folder in video_folders:
        single_folder = []
        for video_file in video_folder.glob('*.mp4'):
            single_folder.append(video_file)

        for i, video_file in enumerate(single_folder):
            print(f"current movie {video_file.name}")
            cam_type = str(video_file.name)[0]
            if cam_type not in model_paths:
                print(f"Invalid camera type or movie file name {video_file.name}")
            elif cam_type == 'G':
                # Top-down view (Camera G) is ignored 
                continue
            else:
                print(f"Camera: {cam_type}")
                print("model_paths[cam_type]:", model_paths[cam_type])
                print("single_folder[i]:", single_folder[i])
                config_path = os.path.join(model_paths[cam_type], 'config.yaml')

                print(f"config path {config_path}")

                deeplabcut.analyze_videos(config_path, str(single_folder[i]), save_as_csv=True)

                deeplabcut.filterpredictions(config_path, str(single_folder[i]), save_as_csv=True)

                deeplabcut.create_labeled_video(config_path, [str(single_folder[i])], videotype='.mp4', filtered=True)


    