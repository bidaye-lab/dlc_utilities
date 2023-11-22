"""
visualization.py: code to generate VMD visualization from anipose 3D annotation CSV
"""

__author__ = "Nico Spiller"


import pandas as pd
from pathlib import Path
import argparse
from utils import find_nx_dirs

def csv_to_xyz(csv:Path, p_xyz_dir:Path, split=1400, ball=None):
    """
    Create xyz trajectory file(s) from CSV
    
    Args:
        csv (str): Name of the CSV file
        split (int): Split output files to S frames per file. Select 0 for no splitting. Default: 1400
        ball (tuple): Center position of the ball in the format (X, Y, Z)
    """
    print(f"generating XyZ")
    csv = Path(csv) # input CSV
    split = split # number of frames for splitting
    ball = ball # center position of the ball
    scl = 5 # scale for reasonable "bond lengths"

    print('INFO reading file {}'.format(csv))
    df = pd.read_csv(csv) # read CSV into pandas dataframe
    print('INFO scaling distances by {}'.format(scl))
    df = df * scl 

    col_x = [ i for i in df.columns if i.endswith('_x')]
    points = [ i.rstrip('x').rstrip('_') for i in col_x ]
    n = len(points) # number of "atoms"
    if ball:
        n += 1
    print('INFO found {} points'.format(n))

    print('INFO loading data ...')
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

        if ball:
            x, y, z = [ float(i) * scl for i in ball ]
            l = '{} {} {} {}\n'.format('Ball', x, y, z)
            lines.append(l)

    
    if split: # write files with fixed number of frames
        xyz = lambda fid: (csv.stem + '_{}.xyz'.format(fid))
        len_blk = split * ( n + 2 ) # each frame is n + 2 lines long
        fid = 0
        
        if not p_xyz_dir.exists():
            p_xyz_dir.mkdir() # Create directory where xyz files will be stored
        dummy_path = p_xyz_dir / xyz(fid)
        out = open(dummy_path, 'w') # dummy file, will remain empty

        for i, l in enumerate(lines):
            if not i % len_blk:
                out.close() # close previous file
                fid += 1
                print('INFO writing file {}'.format(p_xyz_dir / xyz(fid)))
                out = open(p_xyz_dir / xyz(fid), 'w')

            out.write(l)

        out.close()

        dummy_path.unlink() # remove empty dummy file

    else: # if 0, write one file
        xyz = csv.with_suffix('.xyz')
        print('INFO writing file {}'.format(p_xyz_dir / xyz))
        with open(p_xyz_dir / xyz, 'w') as f:
            f.writelines(lines)

# def add_ball(xyz, x, y, z, s=5):
#     x *= s
#     y *= s
#     z *= s
#     print('INFO: new ball coordinates are (scaled by {})'.format(s))
#     print('      x = {}, y = {}, z = {}'.format(x, y, z))
        
#     ball_line = '{} {} {} {}\n'.format('Ball', x, y, z)

#     print('INFO: reading file {}'.format(xyz))
#     with open(xyz, 'r') as f:
#         first_line = f.readline().strip()
#         n = int(first_line)
#     print('INFO: file header is {}'.format(first_line))

#     if n == 34:
#         print('INFO: updating ball coordinates')
#         new_file = []

#         with open(xyz, 'r') as f:
#             for line in f:

#                 l = line.split()

#                 if l[0] == 'Ball':
#                     line = ball_line

#                 new_file.append(line)

#     elif n == 33:
#         print('INFO: adding ball coordinates')
#         new_file = []

#         with open(xyz, 'r') as f:
#             for line in f:

#                 l = line.split()

#                 if l[0] == '33':
#                     line = '34\n'
                
#                 if l[0] == 'Notum':
#                     new_file.append(line)
#                     new_file.append(ball_line)
#                 else:
#                     new_file.append(line)
#     else:
#         raise ValueError('Incorrect file header, expected 33 or 34')
        
   
#     print('INFO: writing new trajectory to {}'.format(xyz))
#     with open(xyz, 'w') as f:
#         f.writelines(new_file)


# def run():
    
#     # command line parser
#     parser = argparse.ArgumentParser(
#         description='''Add `Ball` coordinates to xyz trajectory file or update `Ball` coordinates''')
#     parser.add_argument('xyz', help='Name of the XYZ file')
#     parser.add_argument('x', help='X position')
#     parser.add_argument('y', help='Y position')
#     parser.add_argument('z', help='Z position')
#     args = parser.parse_args()

#     xyz = Path(args.xyz) # trajectory file
#     x, y, z = float(args.x), float(args.y), float(args.z)

#     add_ball(xyz, x, y, z)

def get_pose_3d_folders(directory):
    path = Path(directory)
    pose_3d_folders = list(path.glob('**/pose-3d'))
    return pose_3d_folders

def gen_3d_visualization(p_parent_dir: Path, split: int=1400, ball: tuple = None, xyz_folder_name: str = 'visualization'):
    for nx_dir in find_nx_dirs(p_parent_dir):
        print(f"FOUND NX DIR:\n {nx_dir}")
        pose_3d_folders = get_pose_3d_folders(nx_dir) # Find all pose_3d folders (contain pose_3d CSV)
        print(*pose_3d_folders)
        for p_pose_3d in pose_3d_folders:
            print(f"POSE 3D FOLDER\n {p_pose_3d}")
            xyz_folder = p_pose_3d / xyz_folder_name
            print(f"xyz_folder\n {xyz_folder}")
            p_csv = next(p_pose_3d.glob('*.csv'))
            print(f"3D CSV\n{p_csv}")
            if not xyz_folder.exists() and p_csv.exists():
                csv_to_xyz(p_csv, xyz_folder, split, ball)

# Debugging
if __name__ == "__main__":
    path = Path(r"C:\Users\ryabinkyj\Documents\testanalyze\RawData\BIN-1")
    gen_3d_visualization(path)