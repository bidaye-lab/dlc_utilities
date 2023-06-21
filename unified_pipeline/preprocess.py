"""
preprocess.py: various preprocessing functions used to prepare data for anipose (from DLC output)
"""

__author__ = "Nico Spiller, Jacob Ryabinky"

import pandas as pd
from pathlib import Path

def csv2hdf(csv_path):
    csv = Path(csv_path)

    # loading CSV into pandas dataframe
    print('INFO: Reading {}'.format(csv))
    df = pd.read_csv(csv, index_col=0, header=[0, 1, 2])
    df.columns.set_levels([df.columns[0][0]], level='scorer')

    # save to disk
    hdf = csv.with_suffix('.h5')
    print('INFO: Writing to file {}'.format(hdf))
    df.to_hdf(hdf, key='df_with_missing', mode='w')

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

# TODO: rename fns to pds not csv to match I/O
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
        print('[INFO] removed {} columns starting with'.format(len(cols), start))

    # filter columns based on end of name
    if end:
        cols = df.loc[ :, df.loc[1, :].apply(lambda x: x.endswith(end)) ].columns
        df = df.loc[:, cols]
        print('[INFO] removed {} columns ending with'.format(len(cols), end))

    return df


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

def df2hdf(df: pd.DataFrame, path: Path, root: Path = Path(r'\\mpfi.org\public\sb-lab\BallSystem_RawData')) -> None:
    """Convert pandas DF provided to hdf format and save with proper name format

    Parameters
    ----------
    df : pd.DataFrame
        Preprocessed pandas dataframe representing DLC CSV data
    path : Path
        Path to the original CSV file
    """
    # Create new file name
    new_path = create_file_path(path,root)
    hdf = new_path.with_suffix('.h5')
    print(f'hdf {hdf}')

    # save to disk
    # print(f"[INFO]: Writing to file {hdf}")
    # df.to_hdf(hdf, key='df_with_missing', mode='w')

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
            newpath.mkdir()
            print(str(newpath))
            traverse_dirs(child, newpath) # recursively call to traverse all subdirs
        elif parent == 'files' and child:
            for file in child:
                if isinstance(file, Path):
                    filepath = path / file.name
                    if not filepath.exists():
                        print(f"[INFO] Moving file {file} to {filepath}")
                        file.rename(filepath) # move the existing file here
                else:
                    filepath = path / file
                    if not filepath.exists():
                        print(f"[INFO] New file created at: {filepath}")
                        # if only file name entered, create at location
                        filepath.touch()

def gen_anipose_files(parent_dir: Path, network_name: str, structure:dict={}) -> None:
    """Generate the necessary anipose file structure given a parent path and a file structure

    Parameters
    ----------
    parent_dir : Path
        Parent directory. This is where anipose folder will be placed
    network_name : str
        The name of network used for DLC annotation
    structure : dict, optional
        The file structure represented as a dictionary, by default {}. If left blank, default will be used. The default will be the minimum required for anipose.
    """
    
    # Generate `project` folder structure for anipose
    project = {}
    for folder in parent_dir.glob('N*'): # find all fly folders (N1-Nx)
        h5_files = []
        ball_folder = parent_dir / folder / 'Ball' 
    
        for file in ball_folder.glob('*.h5'): # Find all .h5 files 
            h5_files.append(file)
        project[folder.name] = {
            'pose-3d': {
                'files': h5_files # h5 files
            }
        }

    if not structure:
        print("[INFO]: using default anipose structure")
        # Default file structure
        structure = {
        'anipose': {    
            'Ball': {
                f'{network_name}': {
                    'calibration':{'files':[]},
                    'project': project, # N1-Nx
                    'files':[]
                },
                'files': ['config.toml']
            },
            'SS': {},
            'files':[]
        }
    }

    traverse_dirs(structure, parent_dir)

# path1 = Path(r'\\mpfi.org\public\sb-lab\BallSystem_RawData\10_P9_StochasticActivation\\Nov2022\\Left-turners\\N1\\Ball\\A-11182022190648-0000DLC_resnet101_camA_augmentedJan18shuffle1_500000.csv')
# path2 = Path(r'Z:\\BallSystem_RawData\\10_P9_StochasticActivation\\Nov2022\\Left-turners\\N1\\Ball\\A-11182022190648-0000DLC_resnet101_camA_augmentedJan18shuffle1_500000.csv')
# root = Path(r'Z:\BallSystem_RawData')
# df2hdf([], path1)
# df2hdf([], path2, root)