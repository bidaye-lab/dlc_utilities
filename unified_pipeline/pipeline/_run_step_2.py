"""
Used to call pipeline_step_2.py from pipeline.py
"""

from pipeline_step_2 import run
from pathlib import Path
import sys
import logging

if __name__=="__main__":
    if len(sys.argv) == 2:
        parent_dir = sys.argv[1]
        logging.info(f"Using parent dir path {parent_dir}.")


        logging.info("Starting to run Anipose.")
        run(Path(parent_dir))
        logging.info("Finished running Anipose.")

        logging.info("Finished running pipeline step 2/2.")
    else:
        print("Expected 1 argument: parent_dir")
else: print("WARNING: only used by pipeline.py; not imported.")