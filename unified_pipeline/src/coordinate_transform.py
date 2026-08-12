"""
Step 5: Fly-centric coordinate transformation.

Transforms all x/y/z coordinates from raw anipose space into a fly-centric
coordinate system defined by:
  - z  : normal to the plane fitted through all ThC (thorax-coxa) joints,
          pointing toward Notum
  - x  : mediolateral axis (mid ThC R→L direction), projected onto ThC plane
  - y  : anterior-posterior axis (cross product ez × ex)
  - origin: midpoint of R-M-ThC and L-M-ThC projected onto ThC plane

Applied per fly (flynum group) to each condition .h5 produced by Step 4.
Saves QC plots alongside the .h5 file.

Adapted from:
  kinematics_analysis/notebooks/old_notebooks/feature_generation/utils.py
"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import settings

logger = logging.getLogger(__name__)
VIDEOS_PATH = Path(settings.videos_path)

_REQUIRED_COLS = [
    'Notum_x', 'R-WH_x', 'L-WH_x',
    'R-M-ThC_x', 'L-M-ThC_x',
]


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _norm_vec(x: np.ndarray) -> np.ndarray:
    return x / np.linalg.norm(x)


def fit_plane_thc(df: pd.DataFrame) -> Tuple[float, float, float]:
    """Fit a plane z = a*x + b*y + c through the time-averaged ThC joint positions.

    Uses all columns ending in 'ThC_x/y/z'. Falls back to subsets of ThC joints
    if the residual is high (> 900), choosing the subset with the lowest residual.

    Returns
    -------
    a, b, c : float
        Coefficients for the plane equation z = a*x + b*y + c
    """
    cols_x = [c for c in df.columns if c.endswith('ThC_x')]

    xs, ys, zs = [], [], []
    for c_x in cols_x:
        c_y = c_x[:-1] + 'y'
        c_z = c_x[:-1] + 'z'
        # use time-averaged positions so temporal noise doesn't affect the plane
        xs.append(df[c_x].mean())
        ys.append(df[c_y].mean())
        zs.append(df[c_z].mean())

    def _lstsq(xs, ys, zs):
        A = np.vstack([xs, ys, np.ones(len(xs))]).T
        return np.linalg.lstsq(A, np.array(zs), rcond=None)

    res = _lstsq(xs, ys, zs)
    residual = res[1].item() if len(res[1]) else 0.0

    if residual > 900:
        logger.warning(f"High residual fitting ThC plane ({residual:.1f}); trying subsets")
        subsets = [
            ['R-F-ThC_x', 'L-M-ThC_x', 'R-H-ThC_x'],
            ['L-F-ThC_x', 'R-M-ThC_x', 'L-H-ThC_x'],
            ['L-M-ThC_x', 'R-M-ThC_x', 'L-H-ThC_x', 'R-H-ThC_x'],
        ]
        best_res, best_residual = res, residual
        for subset in subsets:
            subset = [c for c in subset if c in df.columns]
            if not subset:
                continue
            xs_s = [df[c].mean() for c in subset]
            ys_s = [df[c[:-1] + 'y'].mean() for c in subset]
            zs_s = [df[c[:-1] + 'z'].mean() for c in subset]
            r = _lstsq(xs_s, ys_s, zs_s)
            r_val = r[1].item() if len(r[1]) else 0.0
            if r_val < best_residual:
                best_res, best_residual = r, r_val
        res = best_res
        logger.info(f"Best subset residual: {best_residual:.1f}")

    a, b, c = res[0]
    logger.info(f"ThC plane: a={a:.3f}, b={b:.3f}, c={c:.3f}, residual={residual:.1f}")
    return a, b, c


def construct_basis(
    df: pd.DataFrame, a: float, b: float, c: float
) -> Tuple[np.ndarray, np.ndarray]:
    """Construct the fly-centric transformation matrix T and coordinate origin.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain Notum, R-WH, L-WH, and all ThC xyz columns.
    a, b, c : float
        Coefficients of the ThC plane (z = a*x + b*y + c).

    Returns
    -------
    T : (3, 3) np.ndarray
        Columns are the basis vectors [ex, ey, ez].
    center : (3,) np.ndarray
        Origin of the new coordinate system in old coordinates.
    """
    # Intermediate basis for projecting points onto the ThC plane
    n  = _norm_vec(np.array([-a, -b, 1.0]))
    o  = np.array([0.0, 0.0, c])
    e1 = _norm_vec(np.array([1.0, 0.0, a]))
    e2 = np.cross(e1, n)

    proj12 = lambda p: o + np.dot(p - o, e1) * e1 + np.dot(p - o, e2) * e2

    def _mean(col_prefix):
        cols = [f'{col_prefix}_{i}' for i in 'xyz']
        return df[cols].mean().values

    notum = _mean('Notum')
    rmthc = _mean('R-M-ThC')
    lmthc = _mean('L-M-ThC')

    # z: normal to ThC plane, positive toward Notum
    ez = n if np.dot(n, notum - o) > 0 else -n
    # x: mediolateral axis (R-M-ThC → L-M-ThC projected onto plane)
    ex = _norm_vec(proj12(rmthc) - proj12(lmthc))
    # y: anterior-posterior axis
    ey = np.cross(ez, ex)

    T      = np.vstack([ex, ey, ez]).T
    center = np.mean([proj12(rmthc), proj12(lmthc)], axis=0)

    return T, center


def transform_to_flycentric(df: pd.DataFrame) -> pd.DataFrame:
    """Transform all *_x/y/z columns to fly-centric coordinates.

    Fits the ThC plane and constructs the coordinate basis from time-averaged
    landmark positions, then applies the transformation to every frame.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain ThC, Notum, R-WH, and L-WH xyz columns.

    Returns
    -------
    df_trans : pd.DataFrame
        Copy of df with all *_x/y/z columns replaced by fly-centric coordinates.
    """
    df_trans = df.copy()

    a, b, c = fit_plane_thc(df)
    T, center = construct_basis(df, a, b, c)

    cols_x = [col for col in df.columns if col.endswith('_x')]
    for c_x in cols_x:
        c_y = c_x[:-1] + 'y'
        c_z = c_x[:-1] + 'z'
        if c_y not in df.columns or c_z not in df.columns:
            continue
        xyz = df[[c_x, c_y, c_z]].values.astype(float)
        xyz -= center
        xyz = xyz @ T
        df_trans.loc[df.index, [c_x, c_y, c_z]] = xyz

    return df_trans


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_coord_system(
    df: pd.DataFrame,
    joints: List[str] = ['WH', 'ThC', 'Notum'],
    marker_size: int = 3,
    path: Optional[Path] = None,
) -> None:
    """Plot joint distributions projected onto the three anatomical planes.

    Creates a 3-panel figure (side / top / front views) and saves it if
    `path` is given, otherwise displays it.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with xyz columns for the requested joints.
    joints : list of str
        Joint name fragments to include (matched against column names).
    marker_size : int
        Scatter marker size.
    path : Path, optional
        Save path for the figure (.png). If None, figure is displayed.
    """
    cols = [c for c in df.columns if c[-1] in 'xyz']
    cols = [c for c in cols if c.split('_')[0].split('-')[-1] in joints]

    fig, axarr = plt.subplots(ncols=3, figsize=(15, 5))

    for col_x, col_y, col_z in zip(cols[::3], cols[1::3], cols[2::3]):
        xyz = df[[col_x, col_y, col_z]].values
        x, y, z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
        label = col_x[:-2]

        axarr[0].scatter(y, z, s=marker_size, label=label)
        axarr[1].scatter(x, y, s=marker_size)
        axarr[2].scatter(x, z, s=marker_size)

    titles    = ['side view (y–z)', 'top view (x–y)', 'front view (x–z)']
    xlabels   = ['y (post.→ant.)',   'x (L→R)',         'x (L→R)']
    ylabels   = ['z (vent.→dors.)',  'y (post.→ant.)',   'z (vent.→dors.)']

    for ax, title, xl, yl in zip(axarr, titles, xlabels, ylabels):
        ax.set_title(title)
        ax.set_xlabel(xl)
        ax.set_ylabel(yl)
        ax.axvline(0, ls=':', c='gray', lw=0.8)
        ax.axhline(0, ls=':', c='gray', lw=0.8)

    axarr[0].legend(loc='upper right', fontsize=7, markerscale=2)
    fig.tight_layout()

    if path:
        fig.savefig(path, dpi=150, bbox_inches='tight')
        plt.close(fig)
    else:
        plt.show()


# ---------------------------------------------------------------------------
# Pipeline entry point
# ---------------------------------------------------------------------------

def _has_required_cols(df: pd.DataFrame) -> bool:
    return all(c in df.columns for c in _REQUIRED_COLS)


def run(
    parent_dir: Path = VIDEOS_PATH,
    joints_to_plot: List[str] = ['WH', 'ThC', 'Notum'],
) -> None:
    """Apply fly-centric coordinate transformation to all condition data files.

    Finds every *_data.h5 produced by Step 4 under parent_dir/anipose/*/,
    transforms coordinates per fly, saves a QC plot per fly alongside the
    .h5, then overwrites the .h5 with the transformed data.

    Parameters
    ----------
    parent_dir : Path
        Experiment folder containing an anipose/ subdirectory.
    joints_to_plot : list of str
        Joint name fragments passed to plot_coord_system for QC plots.
    """
    p_anipose = parent_dir / 'anipose'
    if not p_anipose.exists():
        logger.error(f"No anipose/ directory in {parent_dir}")
        return

    num_processed = 0

    for condition_dir in sorted(p_anipose.iterdir()):
        if not condition_dir.is_dir():
            continue

        # Read the Step 4 output; skip files already transformed by this step
        h5_files = sorted(
            f for f in condition_dir.glob('*_data.h5')
            if not f.stem.endswith('_flycentric')
            and not f.stem.endswith('_rescaled')
        )
        if not h5_files:
            logger.info(f"{condition_dir.name}: no Step-4 *_data.h5 found, skipping")
            continue
        h5_path = h5_files[0]

        logger.info(f"Loading {h5_path.name}")
        df = pd.read_hdf(h5_path, key='df')

        if not _has_required_cols(df):
            logger.warning(
                f"{condition_dir.name}: missing ThC/Notum/WH columns required for "
                "coordinate transformation — skipping"
            )
            continue

        plot_dir = condition_dir / 'coord_transform_plots'
        plot_dir.mkdir(exist_ok=True)

        fly_groups = list(df.groupby('flynum'))
        logger.info(
            f"{condition_dir.name}: transforming {len(fly_groups)} fly/flies"
        )

        for flynum, df_fly in fly_groups:
            print(f"  {condition_dir.name} | fly {int(flynum)}: fitting ThC plane...")
            try:
                df_transformed = transform_to_flycentric(df_fly)
            except Exception as e:
                logger.error(
                    f"  {condition_dir.name} | fly {int(flynum)}: "
                    f"transformation failed — {e}"
                )
                continue

            df.loc[df_transformed.index, :] = df_transformed

            plot_path = plot_dir / f'flynum_{int(flynum)}.png'
            plot_coord_system(df_transformed, joints=joints_to_plot, path=plot_path)
            print(f"  Saved plot: {plot_path.name}")

        # Save as a new file; Step 4 output (*_data.h5) is preserved untouched
        out_path = condition_dir / (h5_path.stem + '_flycentric.h5')
        df.to_hdf(out_path, key='df', mode='w')
        print(f"Saved: {out_path.name}  ({len(df):,} frames)")
        num_processed += 1

    print(f"\nFinished: coordinate transformation applied to {num_processed} condition(s).")
