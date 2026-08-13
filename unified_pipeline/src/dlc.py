"""
Run the DLC API on raw videos to analyze videos and generate tracking points
"""

import logging
import os
import shutil
from pathlib import Path

import deeplabcut
import numpy as np
import pandas as pd

import src.file_tools as file_tools
from src.file_tools import load_config
from config import settings, COMMON_FILES

VIDEOS_PATH = Path(settings.videos_path)


def _cam_letter(stem: str) -> str:
    """Extract camera letter from a video stem, handling both 'A' and 'A-11390888' styles."""
    return stem.split('-')[0].upper()


def _count_csv_header_rows(csv_path: Path) -> int:
    """Return the number of header rows in a DLC CSV (rows before the numeric frame index)."""
    with open(csv_path, 'r') as fh:
        for i, line in enumerate(fh):
            try:
                int(line.split(',')[0].strip())
                return i
            except ValueError:
                continue
    return 3  # safe fallback


def _keep_top_prediction(df: pd.DataFrame) -> pd.DataFrame:
    """
    For DLC CSVs with ensemble predictions (4-level columns: scorer > bodypart > pred_idx > coord),
    collapse to the single highest-likelihood prediction per bodypart per frame.
    3-level DataFrames (standard DLC output) are returned unchanged.
    """
    if df.columns.nlevels == 3:
        return df

    scorer    = df.columns.get_level_values(0)[0]
    bodyparts = df.columns.get_level_values(1).unique()

    out = {}
    for bp in bodyparts:
        bp_df        = df[(scorer, bp)]
        pred_indices = bp_df.columns.get_level_values(0).unique()

        all_x = np.stack([bp_df[(p, 'x')].values          for p in pred_indices], axis=1)
        all_y = np.stack([bp_df[(p, 'y')].values          for p in pred_indices], axis=1)
        all_l = np.stack([bp_df[(p, 'likelihood')].values  for p in pred_indices], axis=1)

        best = all_l.argmax(axis=1)
        idx  = np.arange(len(best))

        out[(scorer, bp, 'x')]          = all_x[idx, best]
        out[(scorer, bp, 'y')]          = all_y[idx, best]
        out[(scorer, bp, 'likelihood')] = all_l[idx, best]

    result = pd.DataFrame(out, index=df.index)
    result.columns = pd.MultiIndex.from_tuples(
        result.columns, names=['scorer', 'bodyparts', 'coords'])
    return result


def _render_fly_summary(fly_folder: Path, type_folder: Path, model_paths: dict,
                        video_by_cam: dict, cameras_to_analyze=None,
                        max_frames: int = 1400) -> None:
    """
    Build fly/summary_videos/<condition>/ for one fly/condition combination.

    For each camera: copies filtered CSV + meta.pickle, collapses ensemble predictions
    to the top-likelihood one, crops to max_frames, saves as *_filtered.h5, temporarily
    swaps the H5 next to the original video so DLC can render a labeled video into the
    summary folder, then restores the original H5.
    """
    summary_dir = fly_folder / 'summary_videos' / type_folder.name
    summary_dir.mkdir(parents=True, exist_ok=True)
    logging.info(f"Building summary in {summary_dir}")

    for cam in sorted(video_by_cam.keys()):
        if cameras_to_analyze is not None and cam not in cameras_to_analyze:
            continue
        model_path = model_paths.get(cam)
        if not model_path:
            continue

        mov = video_by_cam[cam]
        filtered_csvs = sorted(mov.parent.glob(f'{mov.stem}*filtered.csv'))
        meta_pickles  = sorted(mov.parent.glob(f'{mov.stem}*meta.pickle'))

        if not filtered_csvs:
            logging.warning(f"No filtered CSV for cam {cam} ({mov.name}) — skipping summary")
            continue

        src_csv = filtered_csvs[-1]
        h5_name = src_csv.stem + '.h5'

        dest_csv = summary_dir / src_csv.name
        shutil.copy2(src_csv, dest_csv)
        if meta_pickles:
            shutil.copy2(meta_pickles[-1], summary_dir / meta_pickles[-1].name)

        n_header = _count_csv_header_rows(dest_csv)
        df = pd.read_csv(dest_csv, header=list(range(n_header)), index_col=0)
        logging.info(f"cam {cam} — {df.columns.nlevels}-level CSV, {len(df)} frames, "
                     f"{df.columns.get_level_values(1).nunique()} bodyparts")

        df_top = _keep_top_prediction(df).iloc[:max_frames]

        summary_h5 = summary_dir / h5_name
        df_top.to_hdf(str(summary_h5), key='df_with_missing', mode='w')
        dest_csv.unlink()

        orig_h5     = mov.parent / h5_name
        orig_h5_bak = mov.parent / (h5_name + '.bak')
        config_path = Path(model_path) / 'config.yaml'

        renamed = False
        try:
            if orig_h5.exists():
                orig_h5.rename(orig_h5_bak)
                renamed = True
            shutil.copy2(summary_h5, orig_h5)

            deeplabcut.create_labeled_video(
                str(config_path),
                [str(mov)],
                videotype='.mp4',
                filtered=True,
                destfolder=str(summary_dir),
            )
            logging.info(f"Summary video rendered for cam {cam}")

        finally:
            if orig_h5.exists():
                orig_h5.unlink()
            if renamed and orig_h5_bak.exists():
                orig_h5_bak.rename(orig_h5)


def analyze_new(
    videos_folders_path: Path = VIDEOS_PATH,
    network_sets_path: Path = COMMON_FILES / "DLC_network_sets.yml",
    cameras_to_analyze: list = None,
    render_summary: bool = False,
    allow_incomplete: bool = False,
) -> None:
    """Run DLC analysis on all fly folders found under videos_folders_path.

    Scans for N* fly folders, detects condition subfolders (Ball / SS / Air / Amp),
    validates that all 8 camera videos (A–H) are present, runs DLC with the
    appropriate network per camera, and optionally renders cropped summary videos.

    Parameters
    ----------
    videos_folders_path : Path
        Root path containing N* fly folders with condition subfolders.
    network_sets_path : Path
        Path to DLC_network_sets.yml defining model paths per condition and camera.
    cameras_to_analyze : list, optional
        Camera letters to process, e.g. ['A', 'B']. None processes all cameras.
    render_summary : bool
        If True, renders labeled summary videos into fly/summary_videos/<condition>/.
    allow_incomplete : bool
        If True, proceeds even when fewer than 8 cameras are found, warning for each
        missing camera instead of skipping the folder entirely.
    """
    network_sets = load_config(network_sets_path)

    condition_map = {
        'ball': network_sets['Ball'],
        'ss':   network_sets['SS'],
        'air':  network_sets['Air'],
        'amp':  network_sets['Amp'],
    }

    expected_cameras = set('ABCDEFGH')
    videos_folders_path = Path(videos_folders_path)

    fly_folders = sorted(
        f for f in videos_folders_path.iterdir()
        if f.is_dir() and f.name.upper().startswith('N')
    )

    if not fly_folders:
        logging.warning(f"No N* fly folders found in {videos_folders_path}")
        return

    for fly_folder in fly_folders:
        for type_folder in sorted(fly_folder.iterdir()):
            if not type_folder.is_dir():
                continue
            type_key = type_folder.name.lower()
            if type_key not in condition_map:
                continue

            model_paths = condition_map[type_key]
            logging.info(f"{fly_folder.name} / {type_folder.name}: starting DLC analysis")

            # Collect all mp4s in the condition folder, excluding summary_videos
            all_videos = [
                v for v in type_folder.glob('**/*.mp4')
                if 'summary_videos' not in v.parts
            ]

            # Map camera letter → video path; warn if duplicates
            video_by_cam: dict = {}
            for v in all_videos:
                cam = _cam_letter(v.stem)
                if cam not in video_by_cam:
                    video_by_cam[cam] = v
                else:
                    logging.warning(
                        f"Duplicate video for cam {cam}: keeping {video_by_cam[cam].name},"
                        f" ignoring {v.name}"
                    )

            found_cams = set(video_by_cam.keys())

            unexpected = found_cams - expected_cameras
            if unexpected:
                logging.warning(f"Unrecognised camera names {sorted(unexpected)} — ignoring")
                for cam in unexpected:
                    del video_by_cam[cam]
                found_cams = set(video_by_cam.keys())

            missing = expected_cameras - found_cams
            if missing:
                if allow_incomplete:
                    for cam in sorted(missing):
                        logging.warning(f"Camera {cam} not found in {type_folder} — skipping")
                    logging.info(
                        f"Proceeding with {len(found_cams)} camera(s): {sorted(found_cams)}"
                    )
                else:
                    logging.warning(
                        f"{type_folder.name}: expected {sorted(expected_cameras)},"
                        f" found {sorted(found_cams)}. Missing: {sorted(missing)}."
                        f" Skipping. (Set allow_incomplete=True to process anyway.)"
                    )
                    continue
            else:
                logging.info(f"Validated {len(all_videos)} videos: {sorted(found_cams)}")

            for cam in sorted(found_cams):
                if cameras_to_analyze is not None and cam not in cameras_to_analyze:
                    continue
                model_path = model_paths.get(cam)
                if not model_path:
                    logging.info(f"Skipping cam {cam}: no model path defined")
                    continue

                mov = video_by_cam[cam]
                config_path = Path(model_path) / 'config.yaml'
                if not config_path.is_file():
                    logging.warning(f"Skipping cam {cam}: config not found at {config_path}")
                    continue

                logging.info(f"Analyzing {mov.name} with {model_path}")
                deeplabcut.analyze_videos(str(config_path), str(mov), save_as_csv=True)
                deeplabcut.filterpredictions(str(config_path), str(mov), save_as_csv=True)

            if render_summary:
                _render_fly_summary(
                    fly_folder, type_folder, model_paths, video_by_cam,
                    cameras_to_analyze=cameras_to_analyze,
                )
