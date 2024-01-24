"""
Used to call pipeline_step_1.py from pipeline.py
"""

import sys
from pathlib import Path
from pipeline_step_1 import run_preprocessing, analyze_new
import logging
logger = logging.getLogger(__name__)

if __name__=="__main__":
    if len(sys.argv) == 2:
        videos = sys.argv[1]
        logger.info(f"Using video path {videos}.")

        logger.info("Starting DLC Analysis.")
        analyze_new(videos)
        logger.info("Finished DLC Analysis.")

        logger.info("Starting DLC post-processing, Anipose pre-processing.")
        run_preprocessing(videos)
        logger.info("Finished DLC post-processing, Anipose pre-processing.")

        logger.info("Finished running pipeline step 1/2.")
    else:
        print("Expected 1 argument: parent_dir")
else: print("WARNING: only used by pipeline.py; not imported.")