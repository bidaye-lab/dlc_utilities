import deeplabcut
from pathlib import Path

'''
This script analyzes videos with DLC
It expects to be executed in the same directory as the config.yaml

'''

# define paths to folders and config
working_dir = Path().absolute()

project_dir = working_dir # / 'camF_FS34_RN101-BidayeLab-2022-10-01'

config = project_dir / 'config.yaml'

video_dir = project_dir / '0_for_2ndIT' / 'select15'
videos = [ str(v) for v in video_dir.glob('*.mp4') ] # convert to string (DLC can't handle pathlib)

# analyze videos
deeplabcut.analyze_videos(config, videos, save_as_csv=True)

deeplabcut.filterpredictions(config, videos, save_as_csv=True)

deeplabcut.create_labeled_video(config, videos, videotype='.mp4', filtered=True)
