# -*- coding: utf-8 -*-
"""
@author: Nico Spiller
"""

import pandas as pd
import numpy as np
from pathlib import Path
import pickle
import argparse

def run():
    
    # command line parser
    parser = argparse.ArgumentParser(
        description='''Create pickled numpy array from CSV file''')
    parser.add_argument('csv', help='Name of the CSV file')
    args = parser.parse_args()
    csv = Path(args.csv)

    print('INFO: Reading {}'.format(csv))
    df = pd.read_csv(csv) # read CSV into pandas dataframe

    col_x = [ i for i in df.columns if i.endswith('_x')]
    joints = [ i.rstrip('_x') for i in col_x ]
    x =  np.array(df.loc[:, [j + '_x' for j in joints]])
    y =  np.array(df.loc[:, [j + '_y' for j in joints]])
    z =  np.array(df.loc[:, [j + '_z' for j in joints]])
    arr = np.stack((x, y, z), axis=2)

    pkl = csv.with_suffix('.pickle')
    print('INFO: Writing to file {}'.format(pkl))
    with open(pkl, 'wb') as f:
        pickle.dump(arr, f)

if __name__ == '__main__':
    run()