"""
Step 6: Metric rescaling to millimetres.

Reads the ChArUco board marker reconstruction (markers.csv) produced by the
Board_reconstruction notebook — or auto-generates it from calibration videos
already present in anipose/<condition>/calibration/ — to determine the scale
factor that converts anipose coordinate units to millimetres.  Applies the
scale to every spatial column in the Step 5 *_data.h5 files and saves the
result as *_data_rescaled.h5 alongside the original — the Step 5 file is not
touched.

Auto-reconstruction
-------------------
If markers_csv is not supplied and cannot be found in common_files/, this step
detects ArUco markers in the calibration videos using OpenCV and triangulates
them with anipose to produce markers.csv automatically.  The sub-project is
written to anipose/<condition>/board_recon/ and is re-used on subsequent runs
(idempotent).

Scale factor derivation
-----------------------
Four corner markers of the calibration board (quad_ids) form a quadrilateral
with a known physical side length (true_length_mm).  The same quadrilateral
is reconstructed in 3D from the calibration videos.  The ratio

    scale_factor = true_length_mm / mean_reconstructed_side_length

gives mm per anipose unit.

Scaled columns
--------------
All columns whose name ends in _x, _y, _z, or _r (coordinates / distances)
and ball-velocity columns x_vel / y_vel / z_vel are multiplied by
scale_factor.  Metadata (flynum, tnum, fnum, SF) and angle columns are
unchanged.

Reference
---------
Z:\\BPN_Project\\_BDN2_alldata\\0_Analyses\\Board_reconstruction.ipynb
"""

import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import settings

logger = logging.getLogger(__name__)
VIDEOS_PATH  = Path(settings.videos_path)
COMMON_FILES = Path(settings.common_files)

_SPATIAL_SUFFIXES = ('_x', '_y', '_z', '_r')
_VEL_COLS         = {'x_vel', 'y_vel', 'z_vel'}

# ArUco dictionary ID lookup (bits, dict_number) → cv2 predefined dict ID
_ARUCO_BITS_OFFSET   = {4: 0, 5: 4, 6: 8, 7: 12}
_ARUCO_DICT_OFFSET   = {50: 0, 100: 1, 250: 2, 1000: 3}


# ---------------------------------------------------------------------------
# Scale factor computation
# ---------------------------------------------------------------------------

def compute_scale_factor(
    markers_csv: Path,
    quad_ids: List[int] = [15, 3, 5, 17],
    true_length_mm: float = 2.0,
) -> Tuple[float, pd.DataFrame]:
    """Compute mm-per-unit scale factor from a board marker reconstruction CSV.

    Parameters
    ----------
    markers_csv : Path
        markers.csv produced by the ChArUco board anipose reconstruction.
        Expected columns: ``<id>_x``, ``<id>_y``, ``<id>_z`` per marker ID.
    quad_ids : list of int
        Four marker IDs defining the calibration quadrilateral in order.
    true_length_mm : float
        Known physical side length of the quadrilateral in mm.

    Returns
    -------
    scale_factor : float
        Multiply anipose units by this to get mm.
    lengths_df : pd.DataFrame
        Per-frame side lengths for each quadrilateral edge (used for QC).
    """
    coords = pd.read_csv(markers_csv)

    side_pairs  = list(zip(quad_ids, quad_ids[1:] + [quad_ids[0]]))
    side_labels = [f"{a}→{b}" for a, b in side_pairs]

    lengths_df = pd.DataFrame(index=coords.index)
    for label, (a, b) in zip(side_labels, side_pairs):
        dx = coords[f'{b}_x'] - coords[f'{a}_x']
        dy = coords[f'{b}_y'] - coords[f'{a}_y']
        dz = coords[f'{b}_z'] - coords[f'{a}_z']
        lengths_df[label] = np.sqrt(dx**2 + dy**2 + dz**2)

    all_vals     = lengths_df.values.flatten()
    all_vals     = all_vals[~np.isnan(all_vals)]
    mean_side    = float(np.mean(all_vals))
    scale_factor = true_length_mm / mean_side

    print(f"\nCalibration board — quad side lengths (marker IDs: {quad_ids})")
    print(f"{'Side':<8}  {'Mean':>10}  {'Median':>10}")
    print("-" * 34)
    for col in lengths_df.columns:
        v = lengths_df[col].dropna()
        print(f"{col:<8}  {v.mean():>10.4f}  {v.median():>10.4f}")
    print("-" * 34)
    print(f"{'Overall':<8}  {mean_side:>10.4f}  {float(np.median(all_vals)):>10.4f}")
    print(
        f"\nScale factor = {true_length_mm:.2f} mm / {mean_side:.4f} units"
        f" = {scale_factor:.6f} mm/unit"
    )

    return scale_factor, lengths_df


def plot_scale_qc(
    lengths_df: pd.DataFrame,
    scale_factor: float,
    true_length_mm: float,
    path: Optional[Path] = None,
) -> None:
    """Two-panel QC figure: side lengths over time and per-side means."""
    expected_units = true_length_mm / scale_factor

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    ax = axes[0]
    for col in lengths_df.columns:
        ax.plot(lengths_df[col].values, lw=0.7, label=col)
    ax.axhline(expected_units, ls='--', c='black', lw=1.2,
               label=f'expected ({expected_units:.4f} units)')
    ax.set_xlabel('Frame')
    ax.set_ylabel('Side length (anipose units)')
    ax.set_title('Calibration board side lengths over time')
    ax.legend(fontsize=8)

    ax = axes[1]
    means = lengths_df.mean()
    bars  = ax.bar(means.index, means.values, color='steelblue', alpha=0.8)
    ax.axhline(expected_units, ls='--', c='black', lw=1.2,
               label=f'expected ({expected_units:.4f} units)')
    ax.set_ylabel('Mean side length (anipose units)')
    ax.set_title(f'Scale factor = {scale_factor:.6f} mm/unit')
    ax.legend(fontsize=8)
    for bar, v in zip(bars, means.values):
        ax.text(bar.get_x() + bar.get_width() / 2, v + expected_units * 0.002,
                f'{v:.4f}', ha='center', va='bottom', fontsize=8)

    fig.tight_layout()
    if path:
        fig.savefig(path, dpi=150, bbox_inches='tight')
        plt.close(fig)
    else:
        plt.show()


# ---------------------------------------------------------------------------
# Rescaling
# ---------------------------------------------------------------------------

def _spatial_cols(df: pd.DataFrame) -> List[str]:
    cols = [c for c in df.columns if any(c.endswith(s) for s in _SPATIAL_SUFFIXES)]
    cols += [c for c in _VEL_COLS if c in df.columns]
    return list(dict.fromkeys(cols))


def rescale_df(df: pd.DataFrame, scale_factor: float) -> pd.DataFrame:
    """Return a copy of df with all spatial/distance/velocity columns scaled to mm."""
    df_scaled = df.copy()
    for col in _spatial_cols(df):
        df_scaled[col] = df_scaled[col] * scale_factor
    return df_scaled


# ---------------------------------------------------------------------------
# Board marker reconstruction (auto-generates markers.csv from calib videos)
# ---------------------------------------------------------------------------

def _aruco_dict_id(bits: int, dict_number: int) -> int:
    """Map (marker_bits, dict_number) from anipose config to a cv2 ArUco dict ID."""
    try:
        return _ARUCO_BITS_OFFSET[bits] + _ARUCO_DICT_OFFSET[dict_number]
    except KeyError:
        raise ValueError(
            f"Unsupported ArUco dictionary: bits={bits}, dict_number={dict_number}. "
            f"Supported bits: {list(_ARUCO_BITS_OFFSET)}, "
            f"dict_numbers: {list(_ARUCO_DICT_OFFSET)}"
        )


def _detect_markers_in_video(
    video_path: Path,
    all_marker_ids: List[int],
    dict_id: int,
) -> pd.DataFrame:
    """Detect ArUco markers in every frame of a calibration video.

    Returns a DLC-format DataFrame with MultiIndex columns
    (scorer='cv2', bodyparts=str(marker_id), coords=x/y/likelihood).
    Undetected markers are NaN.
    """
    import cv2

    try:
        aruco_dict = cv2.aruco.getPredefinedDictionary(dict_id)
        detector   = cv2.aruco.ArucoDetector(aruco_dict, cv2.aruco.DetectorParameters())
        def _detect(frame):
            return detector.detectMarkers(frame)
    except AttributeError:
        # OpenCV < 4.7 fallback
        aruco_dict = cv2.aruco.Dictionary_get(dict_id)
        params     = cv2.aruco.DetectorParameters_create()
        def _detect(frame):
            return cv2.aruco.detectMarkers(frame, aruco_dict, parameters=params)

    cap      = cv2.VideoCapture(str(video_path))
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    cols = pd.MultiIndex.from_product(
        [['cv2'], [str(i) for i in all_marker_ids], ['x', 'y', 'likelihood']],
        names=['scorer', 'bodyparts', 'coords'],
    )
    data = np.full((n_frames, len(cols)), np.nan)

    for frame_idx in range(n_frames):
        ret, frame = cap.read()
        if not ret:
            break
        gray              = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _   = _detect(gray)
        if ids is None:
            continue
        ids_flat = ids.flatten()
        for mid in all_marker_ids:
            hits = np.where(ids_flat == mid)[0]
            if not hits.size:
                continue
            center = corners[hits[0]][0].mean(axis=0)   # mean of 4 marker corners
            col_x  = cols.get_loc(('cv2', str(mid), 'x'))
            col_y  = cols.get_loc(('cv2', str(mid), 'y'))
            col_l  = cols.get_loc(('cv2', str(mid), 'likelihood'))
            data[frame_idx, col_x] = center[0]
            data[frame_idx, col_y] = center[1]
            data[frame_idx, col_l] = 1.0

    cap.release()
    return pd.DataFrame(data, columns=cols)


def reconstruct_board_markers(
    condition_dir: Path,
    all_marker_ids: List[int] = list(range(18)),
    cam_regex: str = r'-([A-Z])',
    board_marker_bits: int = 6,
    board_marker_dict_number: int = 50,
) -> Optional[Path]:
    """Detect ArUco markers in calibration videos and triangulate to 3D.

    Creates ``board_recon/`` inside *condition_dir* (idempotent — skips
    detection + triangulation if markers.csv already exists there).

    Parameters
    ----------
    condition_dir : Path
        One condition subfolder (e.g. ``anipose/Ball``).  Must contain
        ``calibration/calibration.toml`` and calibration videos.
    all_marker_ids : list of int
        ArUco marker IDs present on the board (default 0–17 for a 6×6 board).
    cam_regex : str
        Regex used by anipose to parse the camera name from an H5 filename.
        Default ``'-([A-Z])'`` matches filenames like ``board-A.h5``.
    board_marker_bits : int
        ``board_marker_bits`` from the anipose config (default 6).
    board_marker_dict_number : int
        ``board_marker_dict_number`` from the anipose config (default 50).

    Returns
    -------
    Path or None
        Path to the generated ``markers.csv``, or None if reconstruction
        could not be completed.
    """
    board_recon_dir = condition_dir / 'board_recon'
    markers_out     = board_recon_dir / 'markers.csv'

    # Idempotent: reuse existing reconstruction
    if markers_out.exists():
        logger.info(f"{condition_dir.name}: using existing board_recon/markers.csv")
        return markers_out

    # Require pre-existing camera calibration
    calib_toml = condition_dir / 'calibration' / 'calibration.toml'
    if not calib_toml.exists():
        logger.info(
            f"{condition_dir.name}: no calibration/calibration.toml — "
            "skipping board reconstruction"
        )
        return None

    # Find calibration videos
    calib_dir = condition_dir / 'calibration'
    video_exts = ('*.mp4', '*.MP4', '*.avi', '*.AVI', '*.mkv', '*.MKV')
    videos = []
    for ext in video_exts:
        videos.extend(calib_dir.glob(ext))
    videos = [v for v in videos if re.search(cam_regex, v.stem)]

    if not videos:
        logger.info(
            f"{condition_dir.name}: no calibration videos matching "
            f"cam_regex '{cam_regex}' in calibration/ — skipping reconstruction"
        )
        return None

    # Detect markers
    try:
        import cv2
    except ImportError:
        logger.warning(
            "opencv-python (cv2) is not installed — cannot auto-detect board markers. "
            "Install it with: pip install opencv-contrib-python"
        )
        return None

    dict_id = _aruco_dict_id(board_marker_bits, board_marker_dict_number)
    cam_detections: List[Tuple[str, pd.DataFrame]] = []

    for video_path in sorted(videos):
        m = re.search(cam_regex, video_path.stem)
        if m is None:
            continue
        cam_name = m.group(1)
        print(f"  Detecting markers in {video_path.name} (cam {cam_name})...")
        df = _detect_markers_in_video(video_path, all_marker_ids, dict_id)

        n_detected = (df.xs('likelihood', axis=1, level='coords') == 1.0).any().sum()
        if n_detected == 0:
            logger.warning(f"    No markers detected in {video_path.name}, skipping")
            continue
        print(f"    {n_detected}/{len(all_marker_ids)} markers detected")
        cam_detections.append((cam_name, df))

    if not cam_detections:
        logger.error(
            f"{condition_dir.name}: marker detection failed for all calibration videos"
        )
        return None

    # Build board_recon project structure:
    #   board_recon/
    #     config.toml
    #     calibration/calibration.toml
    #     project/board/pose-2d-filtered/<cam>.h5   ← skip filter step
    pose2d_dir = board_recon_dir / 'project' / 'board' / 'pose-2d-filtered'
    pose2d_dir.mkdir(parents=True, exist_ok=True)
    (board_recon_dir / 'calibration').mkdir(exist_ok=True)

    for cam_name, df in cam_detections:
        h5_path = pose2d_dir / f'board-{cam_name}.h5'
        df.to_hdf(h5_path, key='df_with_missing', mode='w')

    shutil.copy(calib_toml, board_recon_dir / 'calibration' / 'calibration.toml')

    config_text = f"""\
project = 'project'
nesting = 2

[calibration]
board_type = "charuco"
board_size = [6, 6]
board_marker_bits = {board_marker_bits}
board_marker_dict_number = {board_marker_dict_number}
board_marker_length = 0.375
board_square_side_length = 0.5
animal_calibration = false
fisheye = false

[triangulation]
triangulate = true
cam_regex = '{cam_regex}'
cam_align = "A"
ransac = false
optim = false

[filter]
scale_smooth = 2
scale_length = 3
scale_length_weak = 0.5
reproj_error_threshold = 10
score_threshold = 0.1
n_deriv_smooth = 1
"""
    (board_recon_dir / 'config.toml').write_text(config_text)

    # Triangulate
    print(f"  Running anipose triangulate in {board_recon_dir} ...")
    proc = subprocess.run(
        ['anipose', 'triangulate'],
        cwd=board_recon_dir,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        logger.error(
            f"anipose triangulate failed (return code {proc.returncode}):\n"
            f"{proc.stderr}"
        )
        return None

    # Find the pose-3d output CSV and save as markers.csv
    pose3d_dir = board_recon_dir / 'project' / 'board' / 'pose-3d'
    csvs = list(pose3d_dir.glob('*.csv')) if pose3d_dir.exists() else []
    if not csvs:
        logger.error(
            f"{condition_dir.name}: anipose triangulate produced no pose-3d CSV"
        )
        return None

    shutil.copy(csvs[0], markers_out)
    print(f"  Board reconstruction complete → {markers_out}")
    return markers_out


# ---------------------------------------------------------------------------
# Pipeline entry point
# ---------------------------------------------------------------------------

def _find_markers_csv(parent_dir: Path) -> Optional[Path]:
    for candidate in [COMMON_FILES / 'markers.csv', parent_dir / 'markers.csv']:
        if candidate.exists():
            return candidate
    return None


def _auto_reconstruct_markers_csv(
    parent_dir: Path,
    all_marker_ids: List[int],
    board_marker_bits: int,
    board_marker_dict_number: int,
    cam_regex: str,
) -> Optional[Path]:
    """Try to reconstruct markers.csv from the first eligible condition directory."""
    p_anipose = parent_dir / 'anipose'
    if not p_anipose.exists():
        return None
    for condition_dir in sorted(p_anipose.iterdir()):
        if not condition_dir.is_dir():
            continue
        result = reconstruct_board_markers(
            condition_dir,
            all_marker_ids=all_marker_ids,
            cam_regex=cam_regex,
            board_marker_bits=board_marker_bits,
            board_marker_dict_number=board_marker_dict_number,
        )
        if result is not None:
            return result
    return None


def run(
    parent_dir: Path = VIDEOS_PATH,
    markers_csv: Optional[Path] = None,
    quad_ids: List[int] = [15, 3, 5, 17],
    true_length_mm: float = 2.0,
    all_marker_ids: List[int] = list(range(18)),
    board_marker_bits: int = 6,
    board_marker_dict_number: int = 50,
    cam_regex: str = r'-([A-Z])',
) -> None:
    """Rescale fly-centric coordinates from anipose units to millimetres.

    Locates (or auto-generates) a board marker reconstruction (markers.csv)
    to derive a single scale factor that applies to all conditions, then
    writes ``*_data_rescaled.h5`` alongside each condition's
    ``*_data_flycentric.h5`` (produced by Step 5).

    markers.csv is resolved in this order:
      1. Explicit ``markers_csv`` argument
      2. ``common_files/markers.csv`` or ``parent_dir/markers.csv``
      3. ``anipose/<condition>/board_recon/markers.csv`` (existing reconstruction)
      4. Auto-reconstruction from calibration videos using OpenCV + anipose

    Parameters
    ----------
    parent_dir : Path
        Experiment folder containing an ``anipose/`` subdirectory.
    markers_csv : Path, optional
        Explicit path to ``markers.csv``.  Auto-discovered/reconstructed if None.
    quad_ids : list of int
        Four ArUco marker IDs forming the calibration quadrilateral (in order).
        Default ``[15, 3, 5, 17]`` matches the BPN calibration board.
    true_length_mm : float
        Known physical side length of the calibration quadrilateral in mm.
    all_marker_ids : list of int
        All ArUco marker IDs present on the board (used only for reconstruction).
        Default 0–17 matches a 6×6 ChArUco board.
    board_marker_bits : int
        ``board_marker_bits`` value from the anipose config (default 6).
    board_marker_dict_number : int
        ``board_marker_dict_number`` value from the anipose config (default 50).
    cam_regex : str
        Regex for extracting the camera name from an H5 filename (default
        ``'-([A-Z])'``).

    Notes
    -----
    Ball-velocity columns (x_vel, y_vel, z_vel) are scaled by the same
    factor as position columns.
    """
    # ── Locate or auto-generate markers.csv ────────────────────────────────
    if markers_csv is not None:
        markers_csv = Path(markers_csv)
        if not markers_csv.exists():
            logger.warning(f"Provided markers_csv not found: {markers_csv}; will auto-discover")
            markers_csv = None

    if markers_csv is None:
        markers_csv = _find_markers_csv(parent_dir)

    if markers_csv is None:
        print("markers.csv not found — attempting auto-reconstruction from calibration videos...")
        markers_csv = _auto_reconstruct_markers_csv(
            parent_dir, all_marker_ids, board_marker_bits, board_marker_dict_number, cam_regex
        )

    if markers_csv is None:
        logger.error(
            "markers.csv could not be found or reconstructed.\n"
            "  Options:\n"
            "    1. Pass markers_csv=Path(r'...') to run_rescale()\n"
            "    2. Place markers.csv in common_files/\n"
            "    3. Ensure calibration videos and calibration.toml exist in "
            "anipose/<condition>/calibration/"
        )
        return
    markers_csv = Path(markers_csv)

    # ── Compute scale factor ────────────────────────────────────────────────
    scale_factor, lengths_df = compute_scale_factor(markers_csv, quad_ids, true_length_mm)

    # ── Locate anipose directory ─────────────────────────────────────────────
    p_anipose = parent_dir / 'anipose'
    if not p_anipose.exists():
        logger.error(f"No anipose/ directory in {parent_dir}")
        return

    num_saved = 0

    for condition_dir in sorted(p_anipose.iterdir()):
        if not condition_dir.is_dir():
            continue

        # Prefer Step 5 output (*_data_flycentric.h5); fall back to Step 4 output
        flycentric = sorted(condition_dir.glob('*_data_flycentric.h5'))
        raw        = sorted(
            f for f in condition_dir.glob('*_data.h5')
            if not f.stem.endswith('_flycentric')
            and not f.stem.endswith('_rescaled')
        )
        if flycentric:
            h5_path = flycentric[0]
            logger.info(f"{condition_dir.name}: using Step-5 output {h5_path.name}")
        elif raw:
            h5_path = raw[0]
            logger.warning(
                f"{condition_dir.name}: Step-5 flycentric file not found; "
                f"rescaling Step-4 output {h5_path.name}"
            )
        else:
            logger.info(f"{condition_dir.name}: no data .h5 found, skipping")
            continue

        logger.info(f"Rescaling {h5_path.name}")
        df = pd.read_hdf(h5_path, key='df')

        df_scaled = rescale_df(df, scale_factor)

        # QC plot — saved next to the h5
        qc_path = condition_dir / f'{h5_path.stem}_scale_qc.png'
        plot_scale_qc(lengths_df, scale_factor, true_length_mm, path=qc_path)
        print(f"  QC plot saved: {qc_path.name}")

        # Rescaled file — does NOT overwrite the step-5 output
        out_path = condition_dir / (h5_path.stem + '_rescaled.h5')
        df_scaled.to_hdf(out_path, key='df', mode='w')
        print(
            f"  Saved: {out_path.name}  "
            f"({len(df_scaled):,} frames, {len(df_scaled.columns)} cols, "
            f"scale={scale_factor:.6f} mm/unit)"
        )
        num_saved += 1

    print(f"\nFinished: rescaled {num_saved} condition(s) to mm.")
