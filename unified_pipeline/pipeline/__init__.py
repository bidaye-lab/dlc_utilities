import logging
import sys

LOGGING_LEVEL=logging.INFO # change to use settings later
logging.basicConfig(stream=sys.stdout, level=LOGGING_LEVEL)