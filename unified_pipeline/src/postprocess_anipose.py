"""
Step 3b: Fixed-landmark median replacement.

Certain anatomical landmarks (ThC joints, Notum, Wing Hinges) are effectively
fixed on the body and should not vary frame-to-frame.  Any apparent motion in
their triangulated positions is triangulation noise.  This step replaces the
x/y/z coordinates of those landmarks in the anipose pose-3d CSV with the
per-N* median value, collapsing all temporal variation to a single point.

Applied to pose-3d CSVs in-place before Step 4 (data structure generation)
reads them.  The operation is idempotent: applying it a second time leaves the
values unchanged (median of a constant = that constant).
"""

import logging
import re
from pathlib import Path
from typing import List, Optional

import pandas as pd

from config import settings

logger = logging.getLogger(__name__)
VIDEOS_PATH = Path(settings.videos_path)

FIXED_LANDMARKS: List[str] = [
    'R-F-ThC', 'R-M-ThC', 'R-H-ThC',
    'L-F-ThC', 'L-M-ThC', 'L-H-ThC',
    'Notum', 'L-WH', 'R-WH',
]


def _replace_with_median(df: pd.DataFrame, landmarks: List[str]) -> pd.DataFrame:
    """Replace x/y/z of each landmark with its per-file median. Returns modified copy."""
    df = df.copy()
    for landmark in landmarks:
        for coord in ('x', 'y', 'z'):
            col = f'{landmark}_{coord}'
            if col in df.columns:
                df[col] = df[col].median()
    return df


def run_step3b_postprocessing(
    parent_dir: Path = VIDEOS_PATH,
    landmarks: Optional[List[str]] = None,
) -> None:
    """Replace fixed-landmark coordinates with per-N* median in all pose-3d CSVs.

    Iterates every ``anipose/<condition>/project/N*/pose-3d/*.csv`` under
    *parent_dir*, replaces the x/y/z columns of the specified landmarks with
    their per-file median, and overwrites the CSV in-place.

    Parameters
    ----------
    parent_dir : Path
        Experiment folder containing an ``anipose/`` subdirectory.
    landmarks : list of str, optional
        Landmark names to fix.  Defaults to ThC joints, Notum, and Wing Hinges:
        R-F-ThC, R-M-ThC, R-H-ThC, L-F-ThC, L-M-ThC, L-H-ThC, Notum, L-WH, R-WH.
        Names are matched against column prefixes (``<name>_x/y/z``); unrecognised
        names are silently ignored.
    """
    if landmarks is None:
        landmarks = FIXED_LANDMARKS

    p_anipose = parent_dir / 'anipose'
    if not p_anipose.exists():
        logger.error(f"No anipose/ directory in {parent_dir}")
        return

    n_updated = 0

    for condition_dir in sorted(p_anipose.iterdir()):
        if not condition_dir.is_dir():
            continue
        project_dir = condition_dir / 'project'
        if not project_dir.exists():
            continue

        csvs = sorted(
            p for p in project_dir.glob('*/pose-3d/*.csv')
            if re.match(r'^N\d+$', p.relative_to(project_dir).parts[0])
        )
        if not csvs:
            continue

        logger.info(f"{condition_dir.name}: fixing {len(csvs)} pose-3d file(s)")

        for csv_path in csvs:
            fly = csv_path.relative_to(project_dir).parts[0]
            df  = pd.read_csv(csv_path)

            cols_present = [
                f'{lm}_{c}' for lm in landmarks
                for c in ('x', 'y', 'z')
                if f'{lm}_{c}' in df.columns
            ]
            if not cols_present:
                logger.warning(
                    f"  {condition_dir.name}/{fly}: none of the requested landmark "
                    "columns found — skipping"
                )
                continue

            df_fixed = _replace_with_median(df, landmarks)
            df_fixed.to_csv(csv_path, index=False)
            n_updated += 1
            print(
                f"  {condition_dir.name}/{fly}: "
                f"fixed {len(set(c.rsplit('_',1)[0] for c in cols_present))} landmark(s)"
            )

    print(f"\nFinished: updated {n_updated} pose-3d file(s).")
