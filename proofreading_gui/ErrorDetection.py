"""
Fly Proofreading & Error Detection
"""

import itertools
import numpy as np
import pandas as pd
from scipy.signal import savgol_filter
from typing import List, Tuple, Optional, Dict, Any

class ErrorDetection:
    def __init__(
        self,
        angles_path: str,
        coords_path: str,
        start_segment_setup: int = 0,
        segment_length: int = 1400,
        angle_columns: Optional[List[str]] = None,
        length_pairs: Optional[List[Tuple[str, str]]] = None,
        difference_threshold: float = 10.0,
        window_length: int = 24,
        polyorder: int = 8
    ):
        """
        Initialize the ErrorDetection object.
        Args:
            angles_path: Path to the angles CSV file.
            coords_path: Path to the coordinates CSV file.
            start_segment_setup: Initial offset for highlighted segments.
            segment_length: Length of each highlighted segment.
            angle_columns: List of angle columns to process.
            length_pairs: List of tuples specifying segment pairs to check for length outliers.
                         Each tuple should contain (start_segment, end_segment) names.
                         Default: [("TiTa", "TaG")]
            difference_threshold: Threshold for angle outlier detection.
            window_length: Window length for Savitzky-Golay filter.
            polyorder: Polynomial order for Savitzky-Golay filter.
        """
        self.angles_path = angles_path
        self.coords_path = coords_path
        self.start_segment_setup = start_segment_setup
        self.segment_length = segment_length
        self.angle_columns = angle_columns or [
            'L1D_flex', 'R1D_flex', 'L2D_flex', 'R2D_flex', 'L3D_flex', 'R3D_flex'
        ]
        self.length_pairs = length_pairs or [("TiTa", "TaG")]
        self.difference_threshold = difference_threshold
        self.window_length = window_length
        self.polyorder = polyorder
        self.angles_df = pd.read_csv(self.angles_path, engine='python', on_bad_lines='skip')
        self.coords_df = pd.read_csv(self.coords_path, engine='python', on_bad_lines='skip')
        
        # Debug information
        print(f"Angles DataFrame shape: {self.angles_df.shape}")
        print(f"Coords DataFrame shape: {self.coords_df.shape}")
        print(f"Angles DataFrame columns (first 10): {list(self.angles_df.columns[:10])}")
        print(f"Coords DataFrame columns (first 10): {list(self.coords_df.columns[:10])}")
        print(f"Using angle columns: {self.angle_columns}")
        print(f"Using length pairs: {self.length_pairs}")

    @staticmethod
    def get_highlight_segments(total_length: int, start_segment_setup: int, segment_length: int) -> List[Tuple[int, int]]:
        segments = []
        current_start = start_segment_setup
        while current_start < total_length:
            current_end = min(current_start + segment_length, total_length)
            segments.append((current_start, current_end))
            current_start += segment_length + start_segment_setup
        return segments

    @staticmethod
    def get_segment_index_and_relative_frame(frame_idx: int, segments: List[Tuple[int, int]]) -> Tuple[Optional[int], Optional[int]]:
        for i, (start, end) in enumerate(segments):
            if start <= frame_idx < end:
                return i, frame_idx - start
        return None, None

    def find_angle_outliers(self) -> pd.DataFrame:
        all_angle_outliers = []
        total_length = len(self.angles_df.index)
        segments = self.get_highlight_segments(total_length, self.start_segment_setup, self.segment_length)
        for column_name in self.angle_columns:
            angle_series = self.angles_df[column_name]
            smoothed_angle_series = savgol_filter(angle_series, self.window_length, self.polyorder, deriv=0)
            difference = np.abs(angle_series - smoothed_angle_series)
            black_highlighted_frames = difference[difference > self.difference_threshold]
            if black_highlighted_frames.empty:
                continue
            frame_list = black_highlighted_frames.index.tolist()
            outlier_bunches = []
            if frame_list:
                current_bunch = [frame_list[0]]
                for i in range(1, len(frame_list)):
                    if frame_list[i] - frame_list[i-1] > 4:
                        outlier_bunches.append(current_bunch)
                        current_bunch = [frame_list[i]]
                    else:
                        current_bunch.append(frame_list[i])
                outlier_bunches.append(current_bunch)
            if outlier_bunches:
                bunches_with_stats = []
                for bunch in outlier_bunches:
                    bunch_diffs = black_highlighted_frames.loc[bunch]
                    max_diff = bunch_diffs.max()
                    avg_diff = bunch_diffs.mean()
                    bunches_with_stats.append({
                        'bunch': bunch,
                        'max_diff': max_diff,
                        'avg_diff': avg_diff
                    })
                sorted_bunches = sorted(bunches_with_stats, key=lambda x: x['max_diff'], reverse=True)
                for item in sorted_bunches:
                    bunch = item['bunch']
                    avg_diff = item['avg_diff']
                    max_diff = item['max_diff']
                    first_frame_abs = bunch[0]
                    segment_index, start_frame_rel = self.get_segment_index_and_relative_frame(first_frame_abs, segments)
                    _, end_frame_rel = self.get_segment_index_and_relative_frame(bunch[-1], segments)
                    if segment_index is not None and start_frame_rel is not None and end_frame_rel is not None:
                        row = {
                            'Part': column_name,
                            'N': segment_index + 1,
                            'Start_Frame': int(start_frame_rel),
                            'End_Frame': int(end_frame_rel),
                            'Frame_Count': len(bunch),
                            'Max_Difference': f"{max_diff:.2f}",
                            'Avg_Difference': f"{avg_diff:.2f}",
                            'Heat': avg_diff/10
                        }
                        all_angle_outliers.append(row)
        return pd.DataFrame(all_angle_outliers)

    def find_segment_length_outliers(self) -> pd.DataFrame:
        sides = ["R", "L"]
        legs = {"F": "1", "M": "2", "H": "3"}
        total_length = len(self.coords_df.index)
        segments = self.get_highlight_segments(total_length, self.start_segment_setup, self.segment_length)
        highlighted_mask = np.zeros(total_length, dtype=bool)
        for start, end in segments:
            highlighted_mask[start:end] = True
        all_data = []
        for side, (leg_code, leg_num) in itertools.product(sides, legs.items()):
            for seg_start, seg_end in self.length_pairs:
                part_start = f"{side}-{leg_code}-{seg_start}"
                part_end = f"{side}-{leg_code}-{seg_end}"
                cols_start = [f"{part_start}_x", f"{part_start}_y", f"{part_start}_z"]
                cols_end = [f"{part_end}_x", f"{part_end}_y", f"{part_end}_z"]
                if all(col in self.coords_df.columns for col in cols_start + cols_end):
                    start_xyz = self.coords_df[cols_start].astype(float).to_numpy()
                    end_xyz = self.coords_df[cols_end].astype(float).to_numpy()
                    length = np.linalg.norm(end_xyz - start_xyz, axis=1)
                    mean_val = np.mean(length)
                    std_val = np.std(length)
                    if std_val > 0:
                        for frame_idx in range(total_length):
                            if highlighted_mask[frame_idx]:
                                segment_index, relative_frame = self.get_segment_index_and_relative_frame(frame_idx, segments)
                                if segment_index is not None:
                                    z_score = (length[frame_idx] - mean_val) / std_val
                                    row = {
                                        'Part': f"{side}-{leg_num}: {seg_start}-{seg_end}",
                                        'N': segment_index + 1,
                                        'Frame': relative_frame,
                                        'Length': f"{length[frame_idx]:.2f}",
                                        'Mean_Length': f"{mean_val:.2f}",
                                        'Std_Dev': f"{std_val:.2f}",
                                        'Z-score': f"{z_score:.2f}"
                                    }
                                    all_data.append(row)
        return pd.DataFrame(all_data)

    @staticmethod
    def create_error_report(angle_outliers_df: pd.DataFrame, segment_outliers_df: pd.DataFrame) -> pd.DataFrame:
        if angle_outliers_df.empty:
            return pd.DataFrame()
        expanded_rows = []
        for _, row in angle_outliers_df.iterrows():
            initial_error = float(row['Avg_Difference']) / 10
            for frame in range(int(row['Start_Frame']), int(row['End_Frame']) + 1):
                expanded_rows.append({
                    'Part': row['Part'],
                    'N': row['N'],
                    'Frame': frame,
                    'Error': initial_error,
                    'angle_error': initial_error,
                    'length_error': 0.0
                })
        error_df = pd.DataFrame(expanded_rows)
        if segment_outliers_df.empty:
            df = error_df.copy()
            df = df.rename(columns={'Part': 'Outlier_Name'})
            return df.loc[:, ['Outlier_Name', 'Frame', 'N', 'Error', 'angle_error', 'length_error']]
        error_df['Side'] = error_df['Part'].str[0]
        error_df['Number'] = error_df['Part'].str[1]
        segment_outliers_df['Side'] = segment_outliers_df['Part'].str[0]
        segment_outliers_df['Number'] = segment_outliers_df['Part'].str[2]
        for df in [error_df, segment_outliers_df]:
            for col in ['Side', 'Number', 'N', 'Frame']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        segment_outliers_df['Z-score'] = pd.to_numeric(segment_outliers_df['Z-score'], errors='coerce')
        merged_df = pd.merge(
            error_df,
            segment_outliers_df[['Side', 'Number', 'N', 'Frame', 'Z-score']],
            on=['Side', 'Number', 'N', 'Frame'],
            how='left'
        )
        merged_df['Z-score'] = merged_df['Z-score'].fillna(0)
        merged_df['length_error'] = merged_df['Z-score'].abs() / 10
        merged_df['Error'] = merged_df['angle_error'] + merged_df['length_error']
        final_df = merged_df[['Part', 'Frame', 'N', 'Error', 'angle_error', 'length_error']].copy()
        final_df['Outlier_Name'] = final_df['Part']
        final_df = final_df.drop(columns=['Part'])
        return final_df

    @staticmethod
    def bunch_final_errors(error_df: pd.DataFrame) -> pd.DataFrame:
        if error_df.empty:
            return pd.DataFrame()
        bunched_data = []
        error_df = error_df.sort_values(by=['Outlier_Name', 'N', 'Frame']).reset_index(drop=True)
        for name, group in error_df.groupby(['Outlier_Name', 'N']):
            if not isinstance(name, tuple):
                outlier_name, n_region = (name, None)
            else:
                outlier_name, n_region = name
            frames = group['Frame'].tolist()
            errors = group['Error'].tolist()
            angle_errors = group['angle_error'].tolist()
            length_errors = group['length_error'].tolist()
            if not frames:
                continue
            current_bunch_frames = [frames[0]]
            current_bunch_errors = [errors[0]]
            current_bunch_angle_errors = [angle_errors[0]]
            current_bunch_length_errors = [length_errors[0]]
            for i in range(1, len(frames)):
                if frames[i] - frames[i - 1] > 3:
                    start_frame = min(current_bunch_frames)
                    end_frame = max(current_bunch_frames)
                    bunched_data.append({
                        'Outlier_Name': outlier_name,
                        'N': n_region,
                        'Start_Frame': start_frame,
                        'End_Frame': end_frame,
                        'Frame_Count': end_frame - start_frame + 1,
                        'Max_Error': max(current_bunch_errors),
                        'Avg_Error': np.mean(current_bunch_errors),
                        'Max_Angle_Error': max(current_bunch_angle_errors),
                        'Avg_Angle_Error': np.mean(current_bunch_angle_errors),
                        'Max_Length_Error': max(current_bunch_length_errors),
                        'Avg_Length_Error': np.mean(current_bunch_length_errors)
                    })
                    current_bunch_frames = [frames[i]]
                    current_bunch_errors = [errors[i]]
                    current_bunch_angle_errors = [angle_errors[i]]
                    current_bunch_length_errors = [length_errors[i]]
                else:
                    current_bunch_frames.append(frames[i])
                    current_bunch_errors.append(errors[i])
                    current_bunch_angle_errors.append(angle_errors[i])
                    current_bunch_length_errors.append(length_errors[i])
            start_frame = min(current_bunch_frames)
            end_frame = max(current_bunch_frames)
            bunched_data.append({
                'Outlier_Name': outlier_name,
                'N': n_region,
                'Start_Frame': start_frame,
                'End_Frame': end_frame,
                'Frame_Count': end_frame - start_frame + 1,
                'Max_Error': max(current_bunch_errors),
                'Avg_Error': np.mean(current_bunch_errors),
                'Max_Angle_Error': max(current_bunch_angle_errors),
                'Avg_Angle_Error': np.mean(current_bunch_angle_errors),
                'Max_Length_Error': max(current_bunch_length_errors),
                'Avg_Length_Error': np.mean(current_bunch_length_errors)
            })
        return pd.DataFrame(bunched_data)

    def run_full_pipeline(self, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Run the full outlier detection and error analysis pipeline.
        Args:
            output_dir: Optional directory to save outputs. If None, files are not saved.
        Returns:
            Dictionary with all intermediate and final DataFrames.
        """
        angle_outliers_df = self.find_angle_outliers()
        segment_outliers_df = self.find_segment_length_outliers()
        error_report_df = self.create_error_report(angle_outliers_df, segment_outliers_df)
        bunched_errors_df = self.bunch_final_errors(error_report_df)
        if output_dir:
            # angle_outliers_df.to_csv(f'{output_dir}/angle_outliers.csv', index=False)
            # segment_outliers_df.to_csv(f'{output_dir}/segment_length_outliers.csv', index=False)
            # error_report_df.to_csv(f'{output_dir}/outlier_error.csv', index=False)
            bunched_errors_df.to_csv(f'{output_dir}/bunched_outlier_errors.csv', index=False)
        return {
            'angle_outliers': angle_outliers_df,
            'segment_outliers': segment_outliers_df,
            'error_report': error_report_df,
            'bunched_errors': bunched_errors_df
        }
