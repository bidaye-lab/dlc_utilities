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
        description='''Convert CSV file to numpy array with a very specific format.''')
    parser.add_argument('csv', help='Name of the CSV file')
    args = parser.parse_args()
    csv = Path(args.csv)

    # loading CSV into pandas dataframe
    print('INFO: Reading {}'.format(csv))
    df = pd.read_csv(csv) 

    # get column names for joints
    col_x = [ i for i in df.columns if i.endswith('_x')] # only ending with _x
    joints = [ i.rstrip('x').rstrip('_') for i in col_x ] # basename
    joints = joints[:30] + [ joints[32], joints[31], joints[30]] # reorder notum, R-WH, L-WH
    
    # x y and z coordinates for each joint and frame: 1st dimension frames, 2nd dimension joints
    x =  np.array(df.loc[:, [j + '_x' for j in joints]])
    y =  np.array(df.loc[:, [j + '_y' for j in joints]])
    z =  np.array(df.loc[:, [j + '_z' for j in joints]])

    # insert array of nans
    n = np.empty((len(x), 1))
    n[:] = np.nan # array of nans

    idx = [2, 7, 12, 17, 22, 27] # insert nans before given indices
    n_ = np.hstack([n for _ in idx])
    x = np.insert(x, idx, n_, axis=1)
    y = np.insert(y, idx, n_, axis=1)
    z = np.insert(z, idx, n_, axis=1)

    x = np.hstack((x, n, n)) # insert nans at the end
    y = np.hstack((y, n, n))
    z = np.hstack((z, n, n))

    # combine so x y z is 3rd dim
    arr = np.stack((x, y, z), axis=2)

    # save to disk
    npy = csv.with_suffix('.npy')
    print('INFO: Writing to file {}'.format(npy))
    np.save(npy, arr)

if __name__ == '__main__':
    run()
