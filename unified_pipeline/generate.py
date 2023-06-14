import deeplabcut
import pandas as pd
import os
import glob as glob
from pathlib import Path
from utils import load_config

def analyze_new(videos_folders_path: Path) -> None:
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
                print(f"[INFO] Camera: {cam_type}")
                print(f"[INFO] Model path: {model_paths[cam_type]}")
                print("[INFO] Video file path:", single_folder[i])
                config_path = os.path.join(model_paths[cam_type], 'config.yaml')

                print(f"config path {config_path}")

                deeplabcut.analyze_videos(config_path, str(single_folder[i]), save_as_csv=True)

                deeplabcut.filterpredictions(config_path, str(single_folder[i]), save_as_csv=True)

                deeplabcut.create_labeled_video(config_path, [str(single_folder[i])], videotype='.mp4', filtered=True)


    
    # -*- coding: utf-8 -*-


def dlc_csv_fix_point(csv:Path, col_name: str = "F-TaG", n: int = 1) -> pd.DataFrame: 
    """Replace all values in a DEEPLABCUT CSV file for training data with one value. 
    This is useful for a point that should stay fixed. Missing values are conserved. 
    Original file is overwritten, old file is saved as FILENAME_bak.

    Parameters
    ----------
    csv : Path
        File path to CSV data from DLC
    col_name : str, optional
        Name of the columns, by default "F-TaG"
    n : int, optional
        Replace values with nth entry. To replace with the mean of whole column, choose 0, by default 1

    Returns
    -------
    df : pd.DataFrame
        Full dataframe (from DLC CSV) with specified points fixed
    """

    df = pd.read_csv(csv,header=None)
    c = df.loc[3:,df.loc[1, :] == col_name].astype(float) # select columns of interests and here only values

    if n > 0:
        x = c.iloc[n-1, :] # select value (python starts counting at 0)
    else:
        x = c.mean() # calculate mean
        
    c.where( c.isnull(), x, axis=1, inplace=True) # replace all non-nan values with x
    print(f'INFO value in {col_name} replaced with {x.values}')

    df.loc[c.index, c.columns] = c # merge back to full dataframe
    
    # store backup file
    # TODO: backup b4 running all preprocessing steps in another function
    backup = Path(str(csv) + '_backup')
    csv.replace(backup) 
    print(f'INFO backup file saved to {backup}')
    
    return df
    # overwrite original csv file
    # df.to_csv(csv, header=None, index=False)
    # print('INFO file updated {}'.format(csv))

