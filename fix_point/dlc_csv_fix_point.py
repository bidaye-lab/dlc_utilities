# -*- coding: utf-8 -*-
"""
Created on Wed Sep 14 18:30:55 2022

@author: nspiller
"""

import pandas as pd
from pathlib import Path
import argparse

def run():
    
    # command line parser
    parser = argparse.ArgumentParser(
        description='''Replace all values in a DEEPLABCUT CSV file for training data with one value. 
        This is useful for a point that should stay fixed.
        Missing values are conserved.
        Original file is overwritten, old file is saved as FILENAME_bak''')
    parser.add_argument('csv', help='Name of the CSV file')
    parser.add_argument('-s', '--column', metavar='C', help='Name of the columns (default: F-TaG)', default='F-TaG', type=str)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-n', '--entry', metavar='N', type=int, default=1, 
                       help='Replace values with nth entry (default: 1). To replace with mean of whole column, choose 0')
    args = parser.parse_args()
    csv = Path(args.csv)
    s = args.column
    n = args.entry 

    df = pd.read_csv(csv, header=None) # read CSV into pandas dataframe

    c = df.loc[3:,df.loc[1, :] == s].astype(float) # select columns of interests and here only values

    if n > 0:
        x = c.iloc[n-1, :] # select value (python starts counting at 0)
    else:
        x = c.mean() # calculate mean
        
    c.where( c.isnull(), x, axis=1, inplace=True) # replace all non-nan values with x
    print('INFO value in {} replaced with {}'.format(s, x.values))

    df.loc[c.index, c.columns] = c # merge back to full dataframe
    
    # store backup file
    bak = Path(str(csv) + '_bak')
    csv.replace(bak) 
    print('INFO backup file saved to {}'.format(bak))
    
    # overwrite original csv file
    df.to_csv(csv, header=None, index=False)
    print('INFO file updated {}'.format(csv))

if __name__ == '__main__':
    run()
