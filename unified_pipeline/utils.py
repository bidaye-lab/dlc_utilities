"""
utils.py: Utility, helper functions for DLC/Anipose pipeline
"""

__author__ = "Jacob Ryabinky"

import logging
import yaml
from pathlib import Path
import shutil
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

def get_csvs(path: Path) -> list:
    csv_paths = []
    for csv in path.glob("**/*.csv"):
        csv_paths.append(csv)
    return csv_paths

def backup_file(path: Path) -> None:
    backup = Path(str(path) + '_backup')
    path.replace(backup) 
    logging.info(f'backup file saved to {backup}')

def find_nx_dirs(parent_dir: Path) -> list:
    dirs = []
    for n1 in parent_dir.glob('**/N1'):
        parent = n1.parent
        if parent.name != 'project':
            dirs.append(parent)
    return dirs

def get_genotype(path: Path, root: Path) -> Path:
    # Helper function to get genotype for G-cam dummy file
    path_rel = path.relative_to(root)

    genotype = str(path_rel.parts[0]).strip().replace("-", "").replace("_","")
    return genotype

