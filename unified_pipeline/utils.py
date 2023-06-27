"""
utils.py: Utility, helper functions for DLC/Anipose pipeline
"""

__author__ = "Jacob Ryabinky"

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
    print(f'[INFO] backup file saved to {backup}')

def find_nx_dirs(parent_dir: Path) -> list:
    dirs = []
    for n1 in parent_dir.glob('**/N1'):
        parent = n1.parent
        if parent.name != 'project':
            dirs.append(parent)
    return dirs

def create_file_path(path: Path, root: Path) -> Path:
    """Create appropriate filename from a path for each data file in the format GenotypeFlynum-camName, e.g: for camA in the BPN dataset, for fly N1, filename: BPNN1-A

    Parameters
    ----------
    path : Path
        The path to the data file

    Returns
    -------
    Path 
        Path with file name in the format GenotypeFlynum-camName
    """
    
    """
    Directory structure example:

    BallSystem_RawData \ <Genotype info> \ <0+ Subdirectories> \ <N1, N2...Nx> \ <Ball, SS> \ <Video & DLC files>

    Camera name - directly from DLC generated file names
    Fly number - parent of parent of DLC file
    Genotype - Child of root
    """
    path_rel = path.relative_to(root)


    cam_name = str(path.name)[0]
    fly_num = str(path.parent.parent.name).strip()
    genotype = str(path_rel.parts[0]).strip().replace("-", "").replace("_", "")
    file_name = genotype + fly_num + "-" + cam_name
    return path.with_name(file_name).with_suffix(path.suffix)

def traverse_dirs(directory_structure: dict, path: Path = Path('')) -> None:
    """Traverse the directory dict structure and generate analagous file structure

    All directories are dicts but files are represented with the key 'files' and a list of either file names (with extension) or the full path to an existing file.
    If the full path is provided, then the existing file will be moved from that location to the location specified in the dictionary structure.

    Parameters
    ----------
    directory_structure : dict
        File structure represented as a dictionary. 
    path : Path, optional
        Path to parent directory. The dictionary file structure will be generated such that path/<dict structure>, by default Path('')
    """
    for parent, child in directory_structure.items():
        if isinstance(child, dict):
            newpath = (path / parent)
            if not newpath.exists():
                print(f"[INFO] Creating new directory {newpath}")
                newpath.mkdir()
                traverse_dirs(child, newpath) # recursively call to traverse all subdirs
            else:
                print(f"[WARNING] Skipping creating {newpath} because it already exists")
        elif parent == 'filesmv' and child:
            for file in child:
                if isinstance(file, Path):
                    filepath = path / file.name
                    if not filepath.exists():
                        print(f"[INFO] Moving file {file} to {filepath}")
                        file.rename(filepath) # if file path entered, move the existing file here
                else:
                    print(f"[WARNING] Skipping {file}, all files in `filesmv` should be paths")
        elif parent == 'filescp' and child:
            for file in child:
                if isinstance(file, Path):
                    filepath = path / file.name
                    if not filepath.exists():
                        print(f"[INFO] Copying file {file} to {filepath}")
                        shutil.copy(file, filepath)
                else:
                    print(f"[WARNING] Skipping {file}, all files in `filescp` should be paths")
        elif parent == 'filesmk' and child:
            for file in child:
                filepath = path / file
                if not filepath.exists():
                    print(f"[INFO] Creating new file at: {filepath}")
                    # if only file name entered, create at location
                    filepath.touch()
