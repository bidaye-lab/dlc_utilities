"""
Step 1b preprocessing: append missing body-part columns to H-cam filtered CSVs.

The H-cam DLC network covers additional body parts (e.g. R-H-ThC) that are
not present in the other camera networks.  Anipose requires every camera file
to share the same set of body-part columns, so the missing columns must be
appended before the anipose folder structure is created.

The trimming helper (fix_extra_h_filtered_columns) is a recovery tool for
files that accidentally had columns appended twice.  It is NOT run by default.
"""

import os
from pathlib import Path

import pandas as pd

from config import settings

COMMON_FILES = Path(settings.common_files)


def fix_extra_h_filtered_columns(
    root_dir,
    prefix="H",
    suffix="_filtered.csv",
    max_cols_threshold=500,
    n_unique_keep=331,
    header_levels=(0, 1, 2),
):
    """Trim H-cam *_filtered.csv files that have duplicate columns.

    Walks all subfolders under root_dir, finds files starting with prefix and
    ending with suffix. For any file exceeding max_cols_threshold columns, keeps
    only the first n_unique_keep unique columns (left-to-right) and overwrites.
    """
    root_dir = Path(root_dir)
    for csv_path in root_dir.rglob(f"{prefix}*{suffix}"):
        if 'summary_videos' in csv_path.parts:
            continue
        print(f"\nChecking file: {csv_path}")
        try:
            df = pd.read_csv(csv_path, header=list(header_levels))
        except Exception as e:
            print(f"  ERROR reading {csv_path}: {e}")
            continue

        n_cols = df.shape[1]
        print(f"  Columns: {n_cols}")
        if n_cols <= max_cols_threshold:
            print("  -> Below threshold, skipping.")
            continue

        seen = set()
        keep_indices = []
        for i, col in enumerate(df.columns):
            if col not in seen:
                seen.add(col)
                keep_indices.append(i)
                if len(seen) == n_unique_keep:
                    break

        if len(seen) < n_unique_keep:
            print(f"  WARNING: Only {len(seen)} unique columns found (expected {n_unique_keep}). Skipping.")
            continue

        df_trimmed = df.iloc[:, keep_indices]
        print(f"  -> Trimming {n_cols} -> {df_trimmed.shape[1]} columns.")
        df_trimmed.to_csv(csv_path, index=False)
        print("  -> File overwritten.")


def run_step1b_preprocessing(
    videos_path=settings.videos_path,
    common_files=COMMON_FILES,
    trim_duplicates=False,
):
    """Append missing body-part columns to H-cam filtered CSVs for each configured condition.

    Anipose requires all camera files to have the same column set.  For
    conditions where cam-H covers extra body parts, this function appends the
    missing columns from a reference CSV.

    To add a new condition:
      1. Add a 'ConditionName': 'filename.csv' entry to EXTRA_COLS_CSV below
      2. Place the corresponding reference CSV in common_files/

    Parameters
    ----------
    videos_path : str or Path
        Root folder containing N* fly directories.
    common_files : Path
        Folder containing the reference extra-column CSVs.
    trim_duplicates : bool
        If True, run fix_extra_h_filtered_columns first to strip accidentally
        duplicated columns before appending.  Disabled by default — only
        enable if a file was processed more than once in error.
    """
    EXTRA_COLS_CSV = {
        'SS':  'SS_preprocess_extracols.csv',
        'Air': 'Air_preprocess_extracols.csv',
        # 'Amp': 'Amp_preprocess_extracols.csv',
    }

    path = Path(videos_path)

    if trim_duplicates:
        print("--- Step 1b: trimming accidentally duplicated H-cam columns ---")
        fix_extra_h_filtered_columns(root_dir=path)

    for condition, csv_name in EXTRA_COLS_CSV.items():
        print(f"\n--- Step 1b preprocessing: {condition} ---")
        ref_cols = pd.read_csv(common_files / csv_name, header=[0, 1, 2])

        for fly_folder in sorted(os.listdir(path)):
            fly_path = path / fly_folder
            condition_path = fly_path / condition
            if not fly_folder.startswith('N') or not condition_path.is_dir():
                continue
            for cam_path in sorted(condition_path.rglob('H*_filtered.csv')):
                if 'summary_videos' in cam_path.parts:
                    continue
                rel = cam_path.parent.relative_to(condition_path)
                print(f"  Checking: {cam_path.name} in {fly_path.name}/{condition}/{rel}")
                camH = pd.read_csv(cam_path, header=[0, 1, 2])
                check_col = (camH.columns.tolist()[4][0], 'R-H-ThC', 'x')
                if check_col in camH.columns.tolist():
                    print(f"    INFO: Skipping, extra columns already present")
                else:
                    camH_new = pd.concat([camH, ref_cols], axis=1)
                    print(f"    {camH.shape} -> {camH_new.shape}")
                    camH_new.to_csv(cam_path, index=False)
