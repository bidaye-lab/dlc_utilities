# -*- coding: utf-8 -*-
"""
@author: Nico Spiller
"""

import pandas as pd
from pathlib import Path
import argparse

def run():
    
    # command line parser
    parser = argparse.ArgumentParser(
        description='''Create xyz trajectory file from CSV''')
    parser.add_argument('csv', help='Name of the CSV file')
    parser.add_argument('-s', '--split', metavar='S', 
    help='Split output files to S frames per file. Default: 1400', default=1400, type=int)
    # group = parser.add_mutually_exclusive_group()
    # group.add_argument('-n', '--entry', metavar='N', type=int, default=1, 
    #                    help='Replace values with nth entry (default: 1). To replace with mean of whole column, choose 0')
    args = parser.parse_args()
    csv = Path(args.csv)
    split = args.split
    # bx, by, bz = 1556.960000844912, -7245.893156816584, 9129.774962573414

    df = pd.read_csv(csv) # read CSV into pandas dataframe
    df = df * 100 # scale for reasonable "bond lengths"

    col_x = [ i for i in df.columns if i.endswith('_x')]
    points = [ i.rstrip('_x') for i in col_x ]
    n = len(points) # number of "atoms"

    lines = []
    for i in df.index:

        lines.append('{}\n'.format(n) ) # first line: number of atoms
        lines.append('Frame {}\n'.format(i)) # second line: commend

        for j in points: # data lines: atom_name x_coord y_coord z_coord
            x = df.loc[i, j + '_x']
            y = df.loc[i, j + '_y']
            z = df.loc[i, j + '_z']

            l = '{} {} {} {}\n'.format(j, x, y, z)
            lines.append(l)

        # l = '{} {} {} {}\n'.format('Ball', x, y+300, z)
        # lines.append(l)

    
    if split: # write files with fixed number of frames
        xyz = lambda fid: csv.with_name(csv.stem + '_{}.xyz'.format(fid))
        len_blk = split * ( n + 2 ) # each frame is n + 2 lines long
        fid = 0
        out = open(xyz(fid), 'w') # dummy file, will remain empty

        for i, l in enumerate(lines):
            if not i % len_blk:
                out.close() # close previous file
                fid += 1
                out = open(xyz(fid), 'w')

            out.write(l)

        out.close()

        xyz(0).unlink() # remove empty dummy file

    else: # if 0, write one file
        xyz = csv.with_suffix('.xyz')
        with open(xyz, 'w') as f:
            f.writelines(lines)

if __name__ == '__main__':
    run()
