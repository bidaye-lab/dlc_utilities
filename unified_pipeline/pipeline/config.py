from src.file_tools import load_config
from pathlib import Path
import logging

config = load_config('pipeline/config.yml')


VIDEOS_PATH = Path(config["videos_path"])
NETWORKS_PATH= Path(config["networks_path"])
ROOT=Path(config["root"])
COMMON_FILES=Path(config["common_files"])
SAVE_FINAL_CSV = bool(config["save_final_csv"])
SKIP_PREPROCESSING_FUNCTIONS= bool(config["skip_preprocessing_functions"])


# Decide logging level
LOGGING_LEVEL = logging.INFO 
log = str(config["logging_level"])
if LOGGING_LEVEL == "error":
    LOGGING_LEVEL = logging.ERROR 
elif LOGGING_LEVEL == "warning":
    LOGGING_LEVEL = logging.WARNING
elif LOGGING_LEVEL == "debug":
    LOGGING_LEVEL == logging.DEBUG
elif LOGGING_LEVEL == "critical":
    LOGGING_LEVEL == logging.CRITICAL