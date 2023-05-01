# -*- coding: utf-8 -*-
"""
@author: nspiller
"""

import pandas as pd
from pathlib import Path
import argparse

def run():
    
    # command line parser
    parser = argparse.ArgumentParser(
        description='''Remove columns in a DEEPLABCUT CSV based on second rows (bodyparts).
        This is useful when certain joints are badly tracked.
        Original file is overwritten, old file is saved as FILENAME_bak''')
    parser.add_argument('csv', help='Name of the CSV file')
    parser.add_argument('-s', '--startswith', metavar='S', help='Remove column if name starts with S')
    parser.add_argument('-e', '--endswith', metavar='E', help='Remove column if name ends with E')

    args = parser.parse_args()
    csv = Path(args.csv)
    start =  args.startswith
    end = args.endswith

    df = pd.read_csv(csv, header=None) # read CSV into pandas dataframe
    
    # filter columns based on beginning of name
    if start:
        cols = df.loc[ :, df.loc[1, :].apply(lambda x: x.startswith(start)) ].columns
        df = df.drop(columns=cols)
        print('INFO removed {} columns starting with'.format(len(cols), start))

    # filter columns based on end of name
    if end:
        cols = df.loc[ :, df.loc[1, :].apply(lambda x: x.endswith(end)) ].columns
        df = df.loc[:, cols]
        print('INFO removed {} columns ending with'.format(len(cols), end))

    # store backup file
    bak = Path(str(csv) + '_bak')
    csv.replace(bak) 
    print('INFO backup file saved to {}'.format(bak))
    
    # overwrite original csv file
    df.to_csv(csv, header=None, index=False)
    print('INFO file updated {}'.format(csv))

if __name__ == '__main__':
    run()
