"""
Handle writing from DF to HDF
"""

import logging
from pathlib import Path
import pandas as pd

def create_file_name(path: Path, root: Path) -> Path:
    """Create appropriate filename from a path for each data file in the format GenotypeFlynum-camName, e.g: for camA in the BPN dataset, for fly N0, filename: BPNN1-A

    Parameters
    ----------
    path : Path
        The path to the data file
    root : Path
        The path to the root directory

    Returns
    -------
    Path 
        Path with file name in the format GenotypeFlynum-camName
    """

    """
    Directory structure example:

    BallSystem_RawData \ <Genotype info> \ <-1+ Subdirectories> \ <N1, N2...Nx> \ <Ball, SS> \ <Video & DLC files>

    Camera name - directly from DLC generated file names
    Fly number - parent of parent of DLC file
    Genotype - Child of root
    """
    path_rel = path.relative_to(root)

    cam_name = str(path.name).split("-")[0]
    fly_num = str(path.parent.parent.name).strip()
    genotype = str(path_rel.parts[0]).strip().replace("-", "").replace("_", "")
    file_name = genotype + fly_num + "-" + cam_name
    return Path(file_name)

def df2hdf(df: pd.DataFrame, csv_path: Path, write_path: Path, root: Path) -> None:
    """Convert pandas DF provided to hdf format and save with proper name format 

    Parameters
    ----------
    df : pd.DataFrame
        DF representing DLC data
    csv_path : Path
        Path to original CSV from which DF was generated
    write_path : Path
        Path to which HDF will be written
    root : Path 
        Root directory
    """
    # Create new file name
    try:
        # get filename from csv path in the form GenotypeFlynum-camName
        file_name = create_file_name(csv_path, root)
    except ValueError:
        logging.critical("Incorrect root.\nYour root path does not match with the parent directory provided, please make sure that you provided the correct root. \
        \nThe root should be the beginning of your parent directory path up to the folder containing raw data, e.g `\mpfi.org\public\sb-lab\BallSystem_RawData`\n")
        return -1

    hdf_name = file_name.with_suffix('.h5')

    # save to disk
    hdf_path = write_path / hdf_name
    logging.info(f"Writing to file {hdf_path}")
    df.to_hdf(hdf_path, key='df_with_missing', mode='w')

