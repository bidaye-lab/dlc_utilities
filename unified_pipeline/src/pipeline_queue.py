"""
Multi-folder pipeline queue with per-folder checkpointing.

Runs any subset of the seven pipeline steps across a list of experiment
folders, skipping steps already completed (per checkpoint file) and
recording failures so interrupted queues can be resumed.

Quick start
-----------
>>> from src.pipeline_queue import run_queue
>>> run_queue([Path(r"Z:\\exp1"), Path(r"Z:\\exp2")])

To run only specific steps (in their natural order):
>>> run_queue(folders, steps=['anipose', 'datastructure', 'coord_transform', 'rescale'])

To pass extra arguments to a step:
>>> run_queue(folders, step_kwargs={'datastructure': {'ball_vel': False}})

To ignore existing checkpoints and rerun everything:
>>> run_queue(folders, force_rerun=True)

Available step names (in pipeline order):
  dlc, h_cam, preprocess, anipose, datastructure, coord_transform, rescale
"""

import json
import traceback
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from pipeline.pipeline_step_1 import run_preprocessing, analyze_new
from pipeline.pipeline_step_2 import run as run_anipose
from src.preprocess import run_step1b_preprocessing
from src.postprocess_anipose import run_step3b_postprocessing
from src.datastructure import run as run_datastructure
from src.coordinate_transform import run as run_coordinate_transform
from src.rescale import run as run_rescale


# ---------------------------------------------------------------------------
# Step registry
# ---------------------------------------------------------------------------
# Each entry: step_name → (function, kwarg_name_for_folder_path)
# The kwarg names differ across step functions; the registry handles that
# so run_queue does not need to know which name each function uses.

PIPELINE_STEPS: OrderedDict = OrderedDict([
    ('dlc',             (analyze_new,                 'videos_folders_path')),
    ('h_cam',           (run_step1b_preprocessing,    'videos_path')),
    ('preprocess',      (run_preprocessing,           'videos')),
    ('anipose',         (run_anipose,                 'parent_dir')),
    ('postprocess',     (run_step3b_postprocessing,   'parent_dir')),
    ('datastructure',   (run_datastructure,           'parent_dir')),
    ('coord_transform', (run_coordinate_transform,    'parent_dir')),
    ('rescale',         (run_rescale,                 'parent_dir')),
])

_CHECKPOINT_FILENAME = 'pipeline_checkpoint.json'


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

def _load_checkpoint(folder: Path) -> dict:
    path = folder / _CHECKPOINT_FILENAME
    if path.exists():
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {'completed': [], 'failed': {}, 'last_updated': None}


def _save_checkpoint(folder: Path, data: dict) -> None:
    data['last_updated'] = datetime.now().isoformat(timespec='seconds')
    (folder / _CHECKPOINT_FILENAME).write_text(
        json.dumps(data, indent=2), encoding='utf-8'
    )


def reset_checkpoint(folder: Path) -> None:
    """Delete the checkpoint file for a folder (equivalent to force_rerun for that folder)."""
    p = folder / _CHECKPOINT_FILENAME
    if p.exists():
        p.unlink()
        print(f"Checkpoint cleared: {folder.name}")
    else:
        print(f"No checkpoint found for: {folder.name}")


# ---------------------------------------------------------------------------
# Queue runner
# ---------------------------------------------------------------------------

def run_queue(
    folders: List[Path],
    steps: Optional[List[str]] = None,
    step_kwargs: Optional[Dict[str, dict]] = None,
    force_rerun: bool = False,
) -> None:
    """Run pipeline steps for each folder in sequence, with checkpointing.

    Parameters
    ----------
    folders : list of Path
        Experiment folders to process. Each must be a valid experiment root
        (the same directory you would pass to ``analyze_new`` or set as
        ``videos_path`` in settings.toml).
    steps : list of str, optional
        Ordered subset of step names to run. Defaults to all steps in
        pipeline order. Valid names (in order):
        ``dlc``, ``h_cam``, ``preprocess``, ``anipose``, ``postprocess``,
        ``datastructure``, ``coord_transform``, ``rescale``.
        Steps are always executed in pipeline order regardless of the order
        they appear in this list.
    step_kwargs : dict of {step_name: kwargs_dict}, optional
        Extra keyword arguments forwarded to individual step functions,
        e.g. ``{'datastructure': {'ball_vel': False}, 'rescale': {'true_length_mm': 2.0}}``.
    force_rerun : bool
        If True, ignore existing checkpoints and run all requested steps
        even if they were previously completed. Default False.

    Notes
    -----
    A ``pipeline_checkpoint.json`` file is created inside each experiment
    folder to track progress.  Completed steps are skipped on re-run
    unless ``force_rerun=True``.  A step that raises an exception stops
    processing for that folder; subsequent folders are unaffected.
    """
    if step_kwargs is None:
        step_kwargs = {}

    # Validate requested step names
    invalid = [s for s in (steps or []) if s not in PIPELINE_STEPS]
    if invalid:
        raise ValueError(
            f"Unknown step name(s): {invalid}. "
            f"Valid names: {list(PIPELINE_STEPS)}"
        )

    # Determine the ordered list of steps to attempt (preserve pipeline order)
    requested = steps if steps is not None else list(PIPELINE_STEPS)
    ordered_steps = [s for s in PIPELINE_STEPS if s in requested]

    n_folders = len(folders)
    results: Dict[str, str] = {}   # folder.name → 'ok' | 'failed at <step>'

    for folder_idx, folder in enumerate(folders):
        folder = Path(folder)
        sep = '─' * 60
        print(f"\n{sep}")
        print(f"  Folder {folder_idx + 1}/{n_folders}: {folder.name}")
        print(f"  Path: {folder}")
        print(sep)

        if not folder.exists():
            msg = f"Folder does not exist: {folder}"
            print(f"  ERROR: {msg}")
            results[str(folder)] = f"skipped — folder not found"
            # Write a checkpoint entry so the error is visible on re-run
            cp = _load_checkpoint(folder.parent / folder.name) if False else {'completed': [], 'failed': {}, 'last_updated': None}
            cp['failed']['_folder'] = msg
            # Can't save checkpoint to non-existent folder; just skip
            continue

        cp = _load_checkpoint(folder)

        folder_failed = False
        for step_name in ordered_steps:
            fn, path_kwarg = PIPELINE_STEPS[step_name]

            already_done = step_name in cp['completed'] and not force_rerun
            if already_done:
                print(f"\n  [{step_name}] already completed — skipping")
                continue

            print(f"\n  [{step_name}] starting...")
            kwargs = {path_kwarg: folder}
            kwargs.update(step_kwargs.get(step_name, {}))

            try:
                fn(**kwargs)
                # Mark complete
                if step_name not in cp['completed']:
                    cp['completed'].append(step_name)
                cp['failed'].pop(step_name, None)
                _save_checkpoint(folder, cp)
                print(f"  [{step_name}] done")
            except Exception as exc:
                err_msg = f"{type(exc).__name__}: {exc}"
                cp['failed'][step_name] = err_msg
                _save_checkpoint(folder, cp)
                print(f"\n  [{step_name}] FAILED — {err_msg}")
                print("  Traceback (last 3 lines):")
                lines = traceback.format_exc().strip().splitlines()
                for line in lines[-3:]:
                    print(f"    {line}")
                print(f"\n  Stopping this folder. Re-run the queue to resume from [{step_name}].")
                folder_failed = True
                break

        # Per-folder summary
        completed_here = [s for s in ordered_steps if s in cp['completed']]
        if folder_failed:
            failed_step = next(iter(cp['failed']), '?')
            results[str(folder)] = f"failed at [{failed_step}]"
            print(f"\n  Result: FAILED at [{failed_step}]  "
                  f"(completed: {completed_here or 'none'})")
        else:
            results[str(folder)] = 'ok'
            print(f"\n  Result: OK  (completed: {completed_here})")

    # Final summary
    print(f"\n{'═' * 60}")
    print(f"  Queue complete — {n_folders} folder(s)")
    print(f"{'═' * 60}")
    ok_count   = sum(1 for v in results.values() if v == 'ok')
    fail_count = n_folders - ok_count
    for folder_str, status in results.items():
        icon = '✓' if status == 'ok' else '✗'
        print(f"  {icon}  {Path(folder_str).name:<40}  {status}")
    print(f"\n  {ok_count} succeeded, {fail_count} failed/skipped")
