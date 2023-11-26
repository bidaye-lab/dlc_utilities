"""
Used to call pipeline_step_1.py from pipeline.py
"""

import sys
from pathlib import Path
from pipeline_step_1 import run_preprocessing, analyze_new
import logging

if __name__=="__main__":
    if len(sys.argv) == 2:
        videos = sys.argv[1]
        logging.info(f"Using video path {videos}.")

        logging.info("Starting DLC Analysis.")
        analyze_new(videos)
        logging.info("Finished DLC Analysis.")

        logging.info("Starting DLC post-processing, Anipose pre-processing.")
        run_preprocessing(videos)
        logging.info("Finished DLC post-processing, Anipose pre-processing.")

        logging.info("Finished running pipeline step 1/2.")
    else:
        print("Expected 1 argument: parent_dir")
else: print("WARNING: only used by pipeline.py; not imported.")