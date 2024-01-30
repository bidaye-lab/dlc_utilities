"""
All of the pipeline code in one file, no notebooks needed. 
"""

#TODO: pass location of common_files in to make more modular if refactored or common_files moved, changed name, etc

#TODO: pipeline.py should probably go in scripts/ ; maybe make the file location of _run_step_1.py and _run_step_2.py constants in their respective pipeline file and pass that to pipeline.py

import subprocess
from pathlib import Path
import logging
import argparse
logger = logging.getLogger()


parser = argparse.ArgumentParser(prog='Unified Pipeline', description='Runs the unified DLC+Anipose pipeline in one script')
parser.add_argument('dlc_env_name')
parser.add_argument('anipose_env_name')
parser.add_argument('videos_dir', help="Directory with raw videos/movies that the pipeline will be\
                                         run on, or a directory containing multiple experiments'\
                                         raw videos, in which case the pipeline will be run on all.")
parser.add_argument('parent_dir', default=None, help="Parent directory of the experiment, usually the same as `videos_dir`\
                                        Anipose will be run on all valid directories found within `parent_dir`")

args = parser.parse_args()

if not args.parent_dir:
    args.parent_dir = args.videos_dir

ERROR = False
DLC_ENV = args.dlc_env_name
ANIPOSE_ENV = args.anipose_env_name
videos_dir = Path(args.videos_dir).resolve()
parent_dir = Path(args.parent_dir).resolve()

path = Path('pipeline\_run_step_1.py').resolve()
cmd = f'conda run -n {DLC_ENV} python {path} {videos_dir}'
print(cmd)

result=subprocess.run(cmd, capture_output=True,text=True, shell=True) 
print(result.stdout)
if result.stderr:
    logger.critical("Aborting pipeline due to error in step 1.")
    ERROR=True

if not ERROR:
    print("Running pipeline step 2")

    path = Path('pipeline\_run_step_2.py').resolve()
    cmd = f'conda run -n {ANIPOSE_ENV} python {path} {parent_dir}'
    print(cmd)
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True) 
    print(result.stdout)
    if result.stderr:
        ERROR=True
        logger.critical("Aborting pipeline due to error in step 2.")
    
if ERROR:
    logger.warning("Pipeline aborted due to error.")