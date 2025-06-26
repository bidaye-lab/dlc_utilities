
# Mapping of bodypart names to the list of camera labels
cameras = {
    # Right front leg
    'R-F-ThC': ['A', 'B'],
    'R-F-CTr': ['A', 'B', 'H'],
    'R-F-FTi': ['A', 'B', 'H'],
    'R-F-TiTa': ['A', 'B', 'H'],
    'R-F-TaG': ['A', 'B', 'H'],

    # Right mid leg
    'R-M-ThC': ['A', 'B'],
    'R-M-CTr': ['A', 'B', 'H'],
    'R-M-FTi': ['A', 'B', 'H'],
    'R-M-TiTa': ['A', 'B', 'H'],
    'R-M-TaG': ['A', 'B', 'H'],

    # Right hind leg
    'R-H-ThC': ['A', 'C'],
    'R-H-CTr': ['A', 'C'],
    'R-H-FTi': ['A', 'C'],
    'R-H-TiTa': ['A', 'C'],
    'R-H-TaG': ['A', 'C'],

    # Left front leg
    'L-F-ThC': ['D', 'E'],
    'L-F-CTr': ['D', 'E', 'H'],
    'L-F-FTi': ['D', 'E', 'H'],
    'L-F-TiTa': ['D', 'E', 'H'],
    'L-F-TaG': ['D', 'E', 'H'],

    # Left mid leg
    'L-M-ThC': ['D', 'F'],
    'L-M-CTr': ['D', 'F'],
    'L-M-FTi': ['D', 'F'],
    'L-M-TiTa': ['D', 'F'],
    'L-M-TaG': ['D', 'F'],

    # Left hind leg
    'L-H-ThC': ['D', 'F'],
    'L-H-CTr': ['D', 'F'],
    'L-H-FTi': ['D', 'F'],
    'L-H-TiTa': ['D', 'F'],
    'L-H-TaG': ['D', 'F'],

    # Wings
    'L-WH': ['D', 'E'],
    'R-WH': ['A', 'B'],

    # Antennae
    'R-antenna': ['A', 'H'],
    'L-antenna': ['D', 'H'],

    # Notum
    'Notum': ['A', 'D', 'B', 'E'],
}


#naming conversions

naming_conversions = {

    #right
    "R1A_flex": "R-F-ThC",
    "R1A_rot": "R-F-ThC",
    "R1A_abduct": "R-F-ThC",
    "R1B_flex": "R-F-CTr",
    "R1B_rot": "R-F-CTr",
    "R1C_flex": "R-F-FTi",
    "R1C_rot": "R-F-FTi",
    'R1D_flex': 'R-F-TaG',

    'R2A_flex': 'R-M-ThC',
    'R2A_rot': 'R-M-ThC',
    'R2A_abduct': 'R-M-ThC',
    'R2B_flex': 'R-M-CTr',
    'R2B_rot': 'R-M-CTr',
    'R2C_flex': 'R-M-FTi',
    'R2C_rot': 'R-M-FTi',
    'R2D_flex': 'R-M-TaG',

    'R3A_flex': 'R-H-ThC',
    'R3A_rot': 'R-H-ThC',
    'R3A_abduct': 'R-H-ThC',
    'R3B_flex': 'R-H-CTr',
    'R3B_rot': 'R-H-CTr',
    'R3C_flex': 'R-H-FTi',
    'R3C_rot': 'R-H-FTi',
    'R3D_flex': 'R-H-TaG',

    #left
    'L1A_flex': 'L-F-ThC',
    'L1A_rot': 'L-F-ThC',
    'L1A_abduct': 'L-F-ThC',
    'L1B_flex': 'L-F-CTr',
    'L1B_rot': 'L-F-CTr',
    'L1C_flex': 'L-F-FTi',
    'L1C_rot': 'L-F-FTi',
    'L1D_flex': 'L-F-TaG',

    'L2A_flex': 'L-M-ThC',
    'L2A_rot': 'L-M-ThC',
    'L2A_abduct': 'L-M-ThC',
    'L2B_flex': 'L-M-CTr',
    'L2B_rot': 'L-M-CTr',
    'L2C_flex': 'L-M-FTi',
    'L2C_rot': 'L-M-FTi',
    'L2D_flex': 'L-M-TaG',

    'L3A_flex': 'L-H-ThC',
    'L3A_rot': 'L-H-ThC',
    'L3A_abduct': 'L-H-ThC',
    'L3B_flex': 'L-H-CTr',
    'L3B_rot': 'L-H-CTr',
    'L3C_flex': 'L-H-FTi',
    'L3C_rot': 'L-H-FTi',
    'L3D_flex': 'L-H-TaG',
}

naming_conversions_reverse = {v: k for k, v in naming_conversions.items()}

joint_conversions = {
    'ThC': 'A',
    'CTr': 'B',
    'FTi': 'C',
    'TiTa': 'D',
}

joint_conversions_reverse = {v: k for k, v in joint_conversions.items()}