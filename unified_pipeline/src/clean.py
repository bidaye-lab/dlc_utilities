"""
Any preprocessing functions that will run on the DLC output before it is sent to Anipose will go here

Note: all make changes to *copy* of the original DF and return a copy.
Note: all operate on the multi-indexed dataframe that has index ('scorer', 'bodyparts', 'coords')
"""

import pandas as pd

def replace_likelihood(df: pd.DataFrame) -> pd.DataFrame:
    """
    Replace `likelihood` column values with 1.0
    """
    
    df_new = df.copy() 

    MAX_LIKELIHOOD = 1.0

    # Selects all from other two indexes and then only `likelihood` from the third (coord)
    df_new.loc[:, (slice(None), slice(None), 'likelihood')] = MAX_LIKELIHOOD

    return df_new

#! Note: fix point only on x,y not x2,y2,...xn,yn; can be changed if necessary to have x2..xn and y2..yn
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
    new_df = df.copy()

    for bodypart in col_names:
        for scorer in df.columns.levels[0]:
            x_tuple = (scorer, bodypart, 'x')
            y_tuple = (scorer, bodypart, 'y')

            if x_tuple in df.columns and y_tuple in df.columns:
                # Select 'x' and 'y' columns for the bodypart
                x_col = df[x_tuple]
                y_col = df[y_tuple]

                # masks for non-missing values
                x_mask = x_col.notna()
                y_mask = y_col.notna()

                # Calculate replacement values
                if n > 0 and len(x_col[x_mask]) >= n and len(y_col[y_mask]) >= n:
                    # Select value at nth position (n-1th index)
                    x_replace_value = x_col[x_mask].iloc[n-1]
                    y_replace_value = y_col[y_mask].iloc[n-1]
                else:
                    x_replace_value = x_col[x_mask].mean()
                    y_replace_value = y_col[y_mask].mean()

                # Update the 'x' and 'y' columns in new_df for non-missing values
                new_df.loc[x_mask, x_tuple] = x_replace_value
                new_df.loc[y_mask, y_tuple] = y_replace_value

    return new_df

def remove_cols(df: pd.DataFrame, start) -> pd.DataFrame:
    """Remove columns in a DEEPLABCUT CSV based on second rows (bodyparts).
        This is useful when certain joints are badly tracked.

    Parameters
    ----------
    df : pd.DataFrame
        Panda DataFrame representing CSV data 
    start : str
        Remove column if name starts with given string 

    Returns
    -------
    DataFrame
        Full dataframe (representing DLC CSV) with columns removed
    """

    # filter columns based on beginning of name
    filter =[col for col in df if col[1].startswith(start)] # Select all cols that have 'bodyparts' column start with `start`
    new_df = df.copy()
    new_df.drop(columns=filter, inplace=True)

    return new_df

