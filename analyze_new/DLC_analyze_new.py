import deeplabcut
import os
import glob as glob
from pathlib import Path

def analyze_new(videos_folders_path):
    
    model_paths = {
        'A': 'C:\\DLC\\3D_8cam_vid\\camA_FS34_RN101-BidayeLab-2022-09-20',
        'B':'C:\\DLC\\3D_8cam_vid\\3cam_BEH-BidayeLab-2022-09-16',
        'C':'C:\\DLC\\3D_8cam_vid\\camC_FS34_RN101-BidayeLab-2022-10-01',
        'D':'C:\\DLC\\3D_8cam_vid\\camD_FS34_RN101-BidayeLab-2022-09-20',
        'E':'C:\\DLC\\3D_8cam_vid\\3cam_BEH-BidayeLab-2022-09-16',
        'F':'C:\\DLC\\3D_8cam_vid\\camF_FS34_RN101-BidayeLab-2022-10-01',
        'G': None, # Top-down view ignored, no model
        'H':'C:\\DLC\\3D_8cam_vid\\3cam_BEH-BidayeLab-2022-09-16'
    }
   
    video_folders = []
    for folder in videos_folders_path.glob('*/Ball'):
        video_folders.append(folder)
    
    for i in range(0, len(video_folders)):
        single_folder = []
        for idx in video_folders[i].glob('*.mp4'):
            single_folder.append(idx)

        for i, idx in enumerate(single_folder):
            print(f"current movie {idx.name}")
            cam_type = str(idx.name)[0]
            if cam_type not in model_paths:
                print("Invalid camera type or movie file name")
            elif cam_type == 'G':
                # Top-down view (Camera G) is ignored 
                continue
            else:
                print(f"Camera: {cam_type}")
                print("model_paths[cam_type]:", model_paths[cam_type])
                print("single_folder[i]:", single_folder[i])
                config_path = os.path.join(model_paths[cam_type], 'config.yaml')

                deeplabcut.analyze_videos(config_path, str(single_folder[i]), save_as_csv=True)

                deeplabcut.filterpredictions(config_path, str(single_folder[i]), save_as_csv=True)

                deeplabcut.create_labeled_video(config_path, [str(single_folder[i])], videotype='.mp4', filtered=True)