# -*- coding: utf-8 -*-
"""
preprocess.py: various preprocessing functions used to prepare data for anipose (from DLC output)
"""
__author__ = "Nico Spiller"

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

def dlc_csv_fix_point(df:pd.DataFrame, col_name: str = "F-TaG", n: int = 1) -> pd.DataFrame: 
    """Replace all values in a DEEPLABCUT CSV file for training data with one value. 
    This is useful for a point that should stay fixed. Missing values are conserved. 
    Original file is overwritten, old file is saved as FILENAME_bak.

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

def dlc_csv_remove_cols(df:pd.DataFrame, start: str = "", end: str = "", ) -> pd.DataFrame:
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


def create_file_path(path: Path) -> Path:
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
    cam_name = str(path.name)[0]
    fly_num = str(path.parent.parent.name).strip()
    genotype = str(path.parts[1]).strip().replace("-", "").replace("-", "")
    file_name = genotype + fly_num + "-" + cam_name
    return path.with_name(file_name).with_suffix(path.suffix)

def df2hdf(df: pd.DataFrame, path: Path) -> None:
    """Convert pandas DF provided to hdf format and save with proper name format

    Parameters
    ----------
    df : pd.DataFrame
        Preprocessed pandas dataframe representing DLC CSV data
    path : Path
        Path to the original CSV file
    """
    # Create new file name
    new_path = create_file_path(path)


    # save to disk
    hdf = new_path.with_suffix('.h5')
    print(f"[INFO]: Writing to file {hdf}")
    df.to_hdf(hdf, key='df_with_missing', mode='w')


def traverse_dirs(directory, path: Path = Path('')):
    for parent, child in directory.items():
        if isinstance(child, dict):
            newpath = (path / parent)
            newpath.mkdir()
            print(str(newpath))
            traverse_dirs(child, newpath) # recursively call to traverse all subdirs
        elif parent == 'files':
            if child:
                for file in child:
                    filepath = path / file
                    print(str(filepath))
                    filepath.touch()

def gen_anipose_files(parent_dir: Path, structure={}:dict):
    network_name = "get from yaml"
    structure = {
        'anipose': {    
            'Ball': {
                f'{network_name}': {
                    'calibration':{'files':[]},
                    'project': {
                        # N1-Nx
                        'files':[]
                    },
                    'files':[]
                },
                'files': ['config.toml']
            },
            'SS': {},
            'files':[]
        }
    }
    # (parent_dir / 'anipose').mkdir()

    traverse_dirs(structure)

network_name='test-network'
structure = {
        'anipose': {
            'Ball': {
                f'{network_name}': {
                    'calibration':{'files':[]},
                    'project': {
                        # N1-Nx
                        'files':['n1','n2','n3']
                    },
                    'files':[]
                },
                'files': ['config.toml']
            },
            'SS': {},
            'files':[]
        }
    }
# list_directories(structure)
traverse_dirs(structure, Path(r'C:\Users\ryabinkyj\Documents\testanalyze'))