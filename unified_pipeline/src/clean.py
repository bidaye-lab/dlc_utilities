"""
Any preprocessing functions that will run on the DLC output before it is sent to Anipose will go here
"""

import logging
import pandas as pd

def fix_point(df: pd.DataFrame, col_names: list, n: int = 1) -> pd.DataFrame:
    """Replace all values in a DataFrame corresponding to DLC CSV data with one value. 
    This is useful for a point that should stay fixed. Missing values are conserved. 
    Original file is overwritten.

    Parameters
    ----------
    df: DataFrame 
        Panda DataFrame representing CSV data 
    col_name : str, optional
        Name of the columns
    n : int, optional
        Replace values with nth entry. To replace with the mean of whole column, choose 0, by default 1

    Returns
    -------
    df : pd.DataFrame
        Full dataframe (representing DLC CSV) with specified points fixed
    """

    # select columns of interests and here only values
    cols = [c for c in df.loc[1, :] if c in col_names]

    c = df.loc[3:,df.loc[1, :].isin(cols)].astype(float) # select columns of interests and here only values

    if n > 0:
        x = c.iloc[n-1, :] # select value index
        logging.info(f'Replacing column values with {n}th value...')
    else:
        x = c.mean() # calculate mean
        logging.info('Replacing column values with mean...')

    for i in x.index:
        c.loc[:, i] = x.loc[i]

    df.loc[c.index, c.columns] = c # merge back to full dataframe

    return df


def remove_cols(df: pd.DataFrame, start: str = "") -> pd.DataFrame:
    """Remove columns in a DEEPLABCUT CSV based on second rows (bodyparts).
        This is useful when certain joints are badly tracked.

    Parameters
    ----------
    df : pd.DataFrame
        Panda DataFrame representing CSV data 
    start : str, optional
        Remove column if name starts with given string, by default ""

    Returns
    -------
    DataFrame
        Full dataframe (representing DLC CSV) with columns removed
    """

    # filter columns based on beginning of name
    if start:
        # find cols with the particular start string
        cols = df.loc[:, df.loc[1, :].apply(
            lambda x: str(x).startswith(start))].columns
        df = df.drop(columns=cols)
        logging.info(
            ' removed {} columns starting with {}'.format(len(cols), start))

    return df
