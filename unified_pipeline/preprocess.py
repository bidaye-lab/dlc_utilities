"""
preprocess.py: various preprocessing functions used to prepare data for anipose (from DLC output)
"""

__author__ = "Nico Spiller, Jacob Ryabinky"

import pickle
pickle.HIGHEST_PROTOCOL = 4
import pandas as pd
from pathlib import Path
import shutil
import utils

def fix_point(df:pd.DataFrame, col_name: str = "F-TaG", n: int = 1) -> pd.DataFrame: 
    """Replace all values in a DataFrame corresponding to DLC CSV data with one value. 
    This is useful for a point that should stay fixed. Missing values are conserved. 
    Original file is overwritten.

    Parameters
    ----------
    df: DataFrame 
        Panda DataFrame representing CSV data 
    col_name : str, optional
        Name of the columns, by default "F-TaG"
    n : int, optional
        Replace values with nth entry. To replace with the mean of whole column, choose 0, by default 1

    Returns
    -------
    df : pd.DataFrame
        Full dataframe (representing DLC CSV) with specified points fixed
    """

    c = df.loc[3:,df.loc[1, :] == col_name].astype(float) # select columns of interests and here only values

    if n > 0:
        x = c.iloc[n-1, :] # select value (python starts counting at 0)
    else:
        x = c.mean() # calculate mean
        
    c.where( c.isnull(), x, axis=1, inplace=True) # replace all non-nan values with x
    print(f'INFO value in {col_name} replaced with {x.values}')

    df.loc[c.index, c.columns] = c # merge back to full dataframe
    
    return df

def remove_cols(df:pd.DataFrame, start: str = "", end: str = "", ) -> pd.DataFrame:
    """Remove columns in a DEEPLABCUT CSV based on second rows (bodyparts).
        This is useful when certain joints are badly tracked.

    Parameters
    ----------
    df : pd.DataFrame
        Panda DataFrame representing CSV data 
    start : str, optional
        Remove column if name starts with given string, by default ""
    end : str, optional
        Remove column if name ends with given string, by default ""

    Returns
    -------
    DataFrame
        Full dataframe (representing DLC CSV) with columns removed
    """

    # filter columns based on beginning of name
    if start:
        cols = df.loc[ :, df.loc[1, :].apply(lambda x: x.startswith(start)) ].columns
        df = df.drop(columns=cols)
        print('[INFO] removed {} columns starting with {}'.format(len(cols), start))

    # filter columns based on end of name
    if end:
        cols = df.loc[ :, df.loc[1, :].apply(lambda x: x.endswith(end)) ].columns
        df = df.loc[:, cols]
        print('[INFO] removed {} columns ending with {}'.format(len(cols), end))

    return df

def clean_dfs(p_csv: Path) -> pd.DataFrame:
    print(f"[INFO] Processing {p_csv.name}")
    csv_df = utils.load_csv_as_df(p_csv)

    # Fix points
    print("[INFO] Running `Fix points` preprocessing...")
    col_names = ['TaG', 'Notum', 'WH']
    n = -1 # Values will be replaced with the nth entry. To replace with the mean, use n=0
    for name in col_names:
        print(f"[INFO] Matching string {name}")
        csv_df = fix_point(csv_df, name, n)

    # Remove cols 
    print("[INFO] Running `Remove cols` preprocessing...")
    camName = p_csv.name[0]
    start = ''
    end = ''
    if camName == 'B':
        print("[INFO] camName `B`, removing cols starting with `L-`")
        start = 'L-' # Remove col if start of name matches string
    if camName == 'E':
        print("[INFO] camName `E`, removing cols starting with `R-`")
        start = 'R-' # Remove col if start of name matches string
    csv_df = remove_cols(csv_df, start, end)
        
    return csv_df

def df2hdf(df: pd.DataFrame, csv_path: Path, write_path: Path, root: Path = Path(r'\\mpfi.org\public\sb-lab\BallSystem_RawData')) -> None:
    """Convert pandas DF provided to hdf format and save with proper name format

    Parameters
    ----------
    df : pd.DataFrame
        Preprocessed pandas dataframe representing DLC CSV data
    path : Path
        Path to the original CSV file
    """
    # Create new file name
    try:
        file_name = utils.create_file_name(csv_path,root)
        # TODO: generate file path
    except ValueError:
        print("[ERROR] Incorrect root.\nYour root path does not match with the parent directory provided, please make sure that you provided the correct root. \
        \nThe root should be the beginning of your parent directory path up to the folder containing raw data, e.g `\mpfi.org\public\sb-lab\BallSystem_RawData`\n")
        return -1
 

    hdf_name = file_name.with_suffix('.h5')

    # save to disk
    hdf_path = write_path / hdf_name
    print(f"[INFO]: Writing to file {hdf_path}")
    df.to_hdf(hdf_path, key='df_with_missing', mode='w')

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
        elif parent == 'filescv':
            for df, csv_path in child:
                # The DF should only be written to the Nx folder it was taken from, 
                # check that DF original Nx folder matches the current path
                csv_nx = csv_path.parent.parent.name
                current_nx_dir = path.parent.name # Nx dir currently being traversed
                if csv_nx == current_nx_dir:
                    print(f"[INFO] CREATING HDF File IN ")
                    df2hdf(df, csv_path, path, Path(r"C:\Users\bidayelab\Documents\SummerIntern\RawData"))
            print(f" the current Nx being traversed is {path.parent.name}")
        elif parent == 'filesmk' and child:
            for file in child:
                filepath = path / file
                if not filepath.exists():
                    print(f"[INFO] Creating new file at: {filepath}")
                    # if only file name entered, create at location
                    filepath.touch()

def gen_anipose_files(parent_dir: Path, p_network_cfg: Path, p_anipose_config: Path, p_calibration_target: Path, p_calibration_timeline: Path, preprocessed_dfs: list, structure:dict={}) -> None:
    """Generate the necessary anipose file structure given a parent path and a file structure

    Parameters
    ----------
    parent_dir : Path
        Parent directory. This is where anipose folder will be placed
    p_network_cfg: Path 
        File path to the config file containing DLC model paths
    p_calibration: Path
        File path to calibration.toml
    p_detection: Path
        File path to detections.pickle
    p_anipose_config:
        File path to config.toml 
    structure : dict, optional
        The file structure represented as a dictionary, by default {}. If left blank, default will be used. The default will be the minimum required for anipose.

        Dictionary mirrors file structure with directories represented by other dictionaries and files represented by lists with three types of keys:\n
             1. `filesmv` - this key takes a list of Path objects and moves the files from the path provided to the new path specified in the dict structure
             2. `filescp` - this key takes a list of Path objects and copies the files from the path provided to the new path specified in the dict structure
             3. `filesmk` - this key takes a list of strings that specify the name and extension of a new file that will be created at the path specified in the dict structure
    """

    # Get anipose calib files based on configs set
    print(f"[INFO] Getting Anipose calibration files...")
    calibration_files = utils.get_anipose_calibration_files(p_calibration_target, p_calibration_timeline, parent_dir)
    
    # Generate `project` folder structure for anipose
    project = {}
    print(f"[INFO] Generating `project` folder structure...")
    for folder in parent_dir.glob('N*'): # find all fly folders (N1-Nx)
        print(f"[INFO] Searching {folder.name} directory")
        csv_files = []
        ball_folder = parent_dir / folder / 'Ball' 
    
        for file in ball_folder.glob('*.csv'): # Find all .csv files 
            if 'filtered' in file.name: # TODO: change to check for model name and cam as well
                print(f"[INFO] Found filtered CSV file {file}")
                csv_files.append(file)
        project[folder.name] = {
            'pose-2d': {
                'filescv': preprocessed_dfs
            },
            'videos-raw':{}
        }
    
    # Get network set name
    cfg = utils.load_config(p_network_cfg)
    network_set_name = cfg['Ball']['name']
    print(f"[INFO] Using network set name {network_set_name}")
    if not structure:
        print("[INFO] Using default anipose file structure")
        # Default file structure
        structure = {
        'anipose': {    
            'Ball': {
                f'{network_set_name}': {
                    'calibration':{'filescp':calibration_files},
                    'project': project, # N1-Nx
                    'filescp':[p_anipose_config]
                },
            },
            'SS': {},
        }
    }

    traverse_dirs(structure, parent_dir)