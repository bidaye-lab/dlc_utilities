__author__ = "Jacob Ryabinky"

import yaml
from pathlib import Path
import pandas as pd


def load_config(path: str):
    """Load config yml as dict.

    Parameters
    ----------
    path: str
        Path to config yml file

    Returns
    -------
    config: dict
        dictionary 
    """

    with open(path, 'r') as f:
        cfg = yaml.safe_load(f)


    return cfg

def load_csv_as_df(csv: Path) -> pd.DataFrame:
    return pd.read_csv(csv, header=None)


def backup_file(path: Path) -> None:
    backup = Path(str(path) + '_backup')
    path.replace(backup) 
    print(f'[INFO] backup file saved to {backup}')

def find_nx_dirs(parent_dir: Path) -> list:
    dirs = []
    for n1 in parent_dir.glob('**/N1'):
        parent = n1.parent
        dirs.append(parent)
    return dirs