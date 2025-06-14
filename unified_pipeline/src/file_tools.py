"""
Functions dealing with file IO, analyzing file path or directory to extract information about experiment
"""

__author__ = "Jacob Ryabinky"

import logging
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

    with open(path, "r") as f:
        cfg = yaml.safe_load(f)

    return cfg


def load_csv_as_df(csv: Path) -> pd.DataFrame:

    # READS AS MULTI-INDEXEDS == does not work with current data preprocess methods

    df = pd.read_csv(csv, index_col=0, header=[0, 1, 2])
    df.columns.set_levels([df.columns[0][0]], level="scorer")
    return df

    # OLD CODE FOR FLAT READING
    # df = pd.read_csv(csv, header=None, low_memory=False) # read CSV into pandas dataframe
    # return df


def get_csvs(path: Path) -> list:
    csv_paths = []
    for csv in path.glob("**/*.csv"):
        csv_paths.append(csv)
    return csv_paths


def backup_file(path: Path) -> None:
    backup = Path(str(path) + "_backup")
    path.replace(backup)
    logging.info(f"backup file saved to {backup}")


def find_nx_dirs(parent_dir: Path) -> list:
    dirs = []
    for n1 in parent_dir.glob("**/N1"):
        parent = n1.parent
        if parent.name != "project":
            dirs.append(parent)
    return dirs


def get_genotype(path: Path, root: Path) -> str:
    # Helper function to get genotype for G-cam dummy file
    path_rel = path.relative_to(root)

    # genotype = str(path_rel.parts[0]).strip().replace("-", "").replace("_","")
    genotype = root.parts[-1] + "_" + path_rel.parts[0]
    print(genotype)
    return genotype
