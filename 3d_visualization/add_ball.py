# -*- coding: utf-8 -*-
"""
@author: Nico Spiller
"""

from pathlib import Path
import argparse


def add_ball(xyz, x, y, z, s=5):

    x *= s
    y *= s
    z *= s
    print('INFO: new ball coordinates are (scaled by {})'.format(s))
    print('      x = {}, y = {}, z = {}'.format(x, y, z))
        
    ball_line = '{} {} {} {}\n'.format('Ball', x, y, z)

    print('INFO: reading file {}'.format(xyz))
    with open(xyz, 'r') as f:
        first_line = f.readline().strip()
        n = int(first_line)
    print('INFO: file header is {}'.format(first_line))

    if n == 34:
        print('INFO: updating ball coordinates')
        new_file = []

        with open(xyz, 'r') as f:
            for line in f:

                l = line.split()

                if l[0] == 'Ball':
                    line = ball_line

                new_file.append(line)

    elif n == 33:
        print('INFO: adding ball coordinates')
        new_file = []

        with open(xyz, 'r') as f:
            for line in f:

                l = line.split()

                if l[0] == '33':
                    line = '34\n'
                
                if l[0] == 'Notum':
                    new_file.append(line)
                    new_file.append(ball_line)
                else:
                    new_file.append(line)
    else:
        raise ValueError('Incorrect file header, expected 33 or 34')
        
   
    print('INFO: writing new trajectory to {}'.format(xyz))
    with open(xyz, 'w') as f:
        f.writelines(new_file)


def run():
    
    # command line parser
    parser = argparse.ArgumentParser(
        description='''Add `Ball` coordinates to xyz trajectory file or update `Ball` coordinates''')
    parser.add_argument('xyz', help='Name of the XYZ file')
    parser.add_argument('x', help='X position')
    parser.add_argument('y', help='Y position')
    parser.add_argument('z', help='Z position')
    args = parser.parse_args()

    xyz = Path(args.xyz) # trajectory file
    x, y, z = float(args.x), float(args.y), float(args.z)

    add_ball(xyz, x, y, z)

if __name__ == '__main__':
    run()