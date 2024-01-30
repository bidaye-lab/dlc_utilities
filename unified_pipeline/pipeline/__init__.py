import logging
import sys
from pipeline.config import LOGGING_LEVEL

logging.basicConfig(stream=sys.stdout, level=LOGGING_LEVEL)