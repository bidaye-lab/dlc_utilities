"""
Step 4: Data structure generation.

Reads anipose outputs (pose-3d, angles) and optional ball velocity data,
concatenates across all N* flies per condition, and saves one .h5 per condition
directly inside that condition's subfolder.

Expected layout
---------------
parent_dir/
  BallVel/              <- only for Ball, requires ball_vel=True
    <N1_...>.csv
  anipose/
    Ball/
      project/
        N1/
          pose-3d/<file>.csv
          angles/<file>.csv
    SS/
      project/
        N1/
          pose-3d/<file>.csv
          angles/<file>.csv
    ...
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

try:
    from natsort import os_sorted
except ImportError:
    def os_sorted(seq):
        return sorted(
            seq,
            key=lambda p: [int(s) if s.isdigit() else s.lower()
                           for s in re.split(r'(\d+)', str(p))]
        )

from config import settings

logger = logging.getLogger(__name__)
VIDEOS_PATH = Path(settings.videos_path)


def _read_pose3d(
    project_dir: Path,
    exclude: List[str],
    n_meta_cols: int = 13,
) -> Dict[str, pd.DataFrame]:
    """Read pose-3d CSVs from project_dir/N*/pose-3d/*.csv, keyed by N* name.

    Drops the last n_meta_cols anipose metadata columns, then keeps only the
    x/y/z coordinates (first 3 of every 6-column landmark group, discarding
    reliability scores).
    """
    depth = len(project_dir.parts)
    csvs = os_sorted([
        p for p in project_dir.glob('*/pose-3d/*.csv')
        if re.match(r'^N\d+$', p.parts[depth])
        and p.parts[depth] not in exclude
    ])
    result: Dict[str, pd.DataFrame] = {}
    for csv_path in csvs:
        fly = csv_path.parts[depth]
        if fly in result:
            logger.warning(f"Multiple pose-3d CSVs for {fly}; using: {csv_path}")
        df = pd.read_csv(csv_path)
        if n_meta_cols > 0:
            df = df.iloc[:, :-n_meta_cols]
        # Keep x/y/z only: first 3 of every 6-column landmark group
        xyz = pd.concat(
            [df.iloc[:, i:i+3] for i in range(0, len(df.columns), 6)],
            axis=1,
        )
        result[fly] = xyz.reset_index(drop=True)
    return result


def _read_angles(
    project_dir: Path,
    exclude: List[str],
) -> Dict[str, pd.DataFrame]:
    """Read angle CSVs from project_dir/N*/angles/*.csv, keyed by N* name."""
    depth = len(project_dir.parts)
    csvs = os_sorted([
        p for p in project_dir.glob('*/angles/*.csv')
        if re.match(r'^N\d+$', p.parts[depth])
        and p.parts[depth] not in exclude
    ])
    result: Dict[str, pd.DataFrame] = {}
    for csv_path in csvs:
        fly = csv_path.parts[depth]
        if fly in result:
            logger.warning(f"Multiple angle CSVs for {fly}; using: {csv_path}")
        df = pd.read_csv(csv_path)
        if 'fnum' in df.columns:
            df = df.drop('fnum', axis=1)
        result[fly] = df.reset_index(drop=True)
    return result


def _read_ballvel(
    parent_dir: Path,
    exclude: List[str],
) -> Dict[str, pd.DataFrame]:
    """Read BallVel CSVs from parent_dir/BallVel/, matched to N* fly names.

    Fly identity is extracted via regex from the filename stem (e.g. N1 in
    'N1_ballvel.csv').  Files whose stem contains no N* pattern are skipped.
    """
    ballvel_dir = parent_dir / 'BallVel'
    if not ballvel_dir.exists():
        return {}
    result: Dict[str, pd.DataFrame] = {}
    for csv_path in os_sorted(list(ballvel_dir.glob('*.csv'))):
        m = re.search(r'N\d+', csv_path.stem)
        if m is None:
            logger.warning(f"Cannot determine fly ID from {csv_path.name}, skipping")
            continue
        fly = m.group()
        if fly in exclude:
            continue
        df = pd.read_csv(csv_path)
        if len(df.columns) >= 3:
            df.columns = ['x_vel', 'y_vel', 'z_vel'] + list(df.columns[3:])
        result[fly] = df.reset_index(drop=True)
    return result


def _align_dicts(
    pos3d: Dict[str, pd.DataFrame],
    angles: Dict[str, pd.DataFrame],
    ballvel: Dict[str, pd.DataFrame],
    trial_len: int,
) -> tuple:
    """Per fly: trim all DataFrames to the same length, rounded down to trial_len."""
    for fly in list(pos3d.keys()):
        if fly not in angles:
            logger.warning(f"No angles data for {fly}, skipping")
            pos3d.pop(fly)
            continue

        lengths = [len(pos3d[fly]), len(angles[fly])]
        if fly in ballvel:
            lengths.append(len(ballvel[fly]))

        n_frames = (min(lengths) // trial_len) * trial_len

        if n_frames == 0:
            logger.warning(f"{fly}: fewer than {trial_len} frames after alignment, skipping")
            pos3d.pop(fly)
            angles.pop(fly, None)
            ballvel.pop(fly, None)
            continue

        if min(lengths) > n_frames:
            logger.info(f"{fly}: trimmed to {n_frames} frames (was {min(lengths)})")

        pos3d[fly]  = pos3d[fly].iloc[:n_frames].reset_index(drop=True)
        angles[fly] = angles[fly].iloc[:n_frames].reset_index(drop=True)
        if fly in ballvel:
            ballvel[fly] = ballvel[fly].iloc[:n_frames].reset_index(drop=True)

    return pos3d, angles, ballvel


def _build_metadata(
    pos3d: Dict[str, pd.DataFrame],
    trial_len: int,
    stim_params_path: Optional[Path] = None,
) -> pd.DataFrame:
    """Build flynum/tnum/fnum columns, optionally adding a stim param (SF) column.

    stim_params_path, if given, should be a CSV whose columns are fly names
    (N1, N2, ...) and rows are per-trial stim parameter values.
    """
    sf_data = None
    if stim_params_path is not None:
        if stim_params_path.exists():
            sf_data = pd.read_csv(stim_params_path)
            logger.info(f"Loaded stim params from {stim_params_path}")
        else:
            logger.warning(f"stim_params_path not found: {stim_params_path}")

    parts = []
    for fly in pos3d.keys():
        n_frames = len(pos3d[fly])
        flynum   = int(re.sub(r'\D', '', fly))
        n_trials = n_frames // trial_len

        tnum_col = sum(([t] * trial_len for t in range(1, n_trials + 1)), [])
        meta = pd.DataFrame({
            'flynum': [flynum] * n_frames,
            'tnum':   tnum_col,
            'fnum':   list(range(n_frames)),
        })

        if sf_data is not None and fly in sf_data.columns:
            sf_list = sum(
                ([val] * trial_len for val in sf_data[fly][:n_trials].tolist()), []
            )
            meta['SF'] = sf_list

        parts.append(meta)

    return pd.concat(parts, ignore_index=True)


def _dicts_to_df(d: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    return pd.concat(list(d.values()), ignore_index=True)


def _build_condition_df(
    condition_dir: Path,
    parent_dir: Path,
    is_ball: bool,
    ball_vel: bool,
    stim_params_path: Optional[Path],
    exclude: List[str],
    trial_len: int,
) -> Optional[pd.DataFrame]:
    project_dir = condition_dir / 'project'
    if not project_dir.exists():
        logger.warning(f"No project/ in {condition_dir}, skipping")
        return None

    pos3d  = _read_pose3d(project_dir, exclude)
    if not pos3d:
        logger.warning(f"No pose-3d data found under {project_dir}")
        return None

    angles = _read_angles(project_dir, exclude)
    bvel   = _read_ballvel(parent_dir, exclude) if (is_ball and ball_vel) else {}

    if is_ball and ball_vel and not bvel:
        msg = f"WARNING: ball_vel=True but BallVel/ not found or empty in {parent_dir}"
        print(msg)
        logger.warning(msg)
        print("  Continuing without ball velocity columns.")

    pos3d, angles, bvel = _align_dicts(pos3d, angles, bvel, trial_len)
    if not pos3d:
        return None

    meta_df  = _build_metadata(pos3d, trial_len, stim_params_path)
    pos3d_df = _dicts_to_df(pos3d)
    angle_df = _dicts_to_df(angles)

    frames = [meta_df, pos3d_df, angle_df]
    if bvel:
        frames.append(_dicts_to_df(bvel))

    combined = pd.concat(frames, axis=1)
    logger.info(
        f"{condition_dir.name}: {len(pos3d)} fly/flies, {len(combined)} total frames"
    )
    return combined


def run(
    parent_dir: Path = VIDEOS_PATH,
    ball_vel: bool = True,
    stim_params_path: Optional[Path] = None,
    exclude: List[str] = [],
    trial_len: int = 1400,
) -> None:
    """Generate concatenated data structures for all conditions under parent_dir/anipose/.

    For each condition subfolder (Ball, SS, Air, Amp, ...):
      - Reads pose-3d and angle CSVs from project/N*/
      - For the Ball condition with ball_vel=True: reads BallVel/ CSVs
      - Builds flynum / tnum / fnum metadata; optionally adds a stim param column (SF)
      - Saves one .h5 file per condition into that condition's subfolder

    Parameters
    ----------
    parent_dir : Path
        Experiment folder containing an anipose/ subdirectory.
    ball_vel : bool
        Include BallVel data for the Ball condition (default True).
        Looks for parent_dir/BallVel/*.csv. If the folder is absent, a warning
        is printed and the dataframe is built without ball velocity columns.
    stim_params_path : Path, optional
        CSV with per-trial stim parameters. Columns are fly names (N1, N2, ...),
        rows are trials. Applied to all conditions that have matching fly columns.
    exclude : list of str
        N* folder names to skip across all conditions (e.g. ['N3', 'N5']).
    trial_len : int
        Number of frames per trial (default 1400).
    """
    p_anipose = parent_dir / 'anipose'
    if not p_anipose.exists():
        logger.error(f"No anipose/ directory in {parent_dir}")
        return

    experiment_name = parent_dir.name
    num_saved = 0

    for condition_dir in sorted(p_anipose.iterdir()):
        if not condition_dir.is_dir():
            continue
        condition = condition_dir.name
        is_ball   = condition.lower() == 'ball'

        logger.info(f"Processing condition: {condition}")
        df = _build_condition_df(
            condition_dir,
            parent_dir       = parent_dir,
            is_ball          = is_ball,
            ball_vel         = ball_vel,
            stim_params_path = stim_params_path,
            exclude          = exclude,
            trial_len        = trial_len,
        )
        if df is None:
            logger.warning(f"Skipped {condition} — no data generated")
            continue

        print(f"\n--- {condition}: preview (first 5 rows, first 12 columns) ---")
        try:
            from IPython.display import display
            display(df.iloc[:5, :12])
        except Exception:
            print(df.iloc[:5, :12].to_string())

        out_path = condition_dir / f"{experiment_name}_{condition}_data.h5"
        df.to_hdf(out_path, key='df', mode='w')
        print(f"Saved: {out_path}  ({len(df):,} frames, {len(df.columns)} columns)")
        num_saved += 1

    print(f"\nFinished: data structures generated for {num_saved} condition(s).")
