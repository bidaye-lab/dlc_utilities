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
        description='''Create xyz trajectory file from CSV''')
    parser.add_argument('csv', help='Name of the CSV file')
    # parser.add_argument('-s', '--column', metavar='C', help='Name of the columns (default: F-TaG)', default='F-TaG', type=str)
    # group = parser.add_mutually_exclusive_group()
    # group.add_argument('-n', '--entry', metavar='N', type=int, default=1, 
    #                    help='Replace values with nth entry (default: 1). To replace with mean of whole column, choose 0')
    args = parser.parse_args(['P9-RightTurner-N4-3Dpose.csv'])
    csv = Path(args.csv)

    df = pd.read_csv(csv) # read CSV into pandas dataframe
    df = df * 100 # scale for reasonable "bond lengths"

    col_x = [ i for i in df.columns if i.endswith('_x')]
    # y = [ i for i in df.columns if i.endswith('_y')]
    # z = [ i for i in df.columns if i.endswith('_z')]

    joints = [ i.rstrip('_x') for i in col_x ]
    
    lines = []
    for i in df.index:
        lines.append( '{}\n'.format(str(len(joints))) )
        lines.append('\n')
        for j in joints:
            x = df.loc[i, j + '_x']
            y = df.loc[i, j + '_y']
            z = df.loc[i, j + '_z']

            a = 'C'
            l = '{} {} {} {}\n'.format(j, x, y, z)
            lines.append(l)
    
    # 
    xyz = csv.with_suffix('.xyz')
    with open(xyz, 'w') as f:
        f.writelines(lines)


if __name__ == '__main__':
    run()
