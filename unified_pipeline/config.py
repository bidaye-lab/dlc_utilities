from pathlib import Path
from dynaconf import Dynaconf

# Anchor to this file's location (unified_pipeline/) so that settings.toml
# and common_files/ are found regardless of the process working directory.
_HERE = Path(__file__).resolve().parent

settings = Dynaconf(
    settings_files=[str(_HERE / 'settings.toml')],
)

# Absolute path to common_files/, resolved relative to unified_pipeline/
COMMON_FILES = (_HERE / settings.common_files).resolve()
