# Proofreading GUI

A comprehensive GUI application built with Python's tkinter for proofreading and correcting DLC (DeepLabCut) assigned joint positions in fly behavior analysis. The application provides an interface for correcting tracking errors in pose estimation data. The application contains built-in error detection algorithms and video playback capabilities.

## Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Installation](#-installation)
- [File Structure](#-expected-file-structure)
- [Usage Guide](#-usage-guide)
- [Configuration](#-configuration)
- [Troubleshooting](#-troubleshooting)
- [Technical Details](#-technical-details)

## 🎯 Overview

The Proofreading GUI is designed specifically for researchers working with fly position data using DeepLabCut and Anipose. It provides:

- **Pose correction** with drag-and-drop
- **Automated error detection** explained in [Error Detection](#-error-detection-system) and more in depth with [Technical Details](#-technical-details)
- **Multi-camera video playback** synchronized with pose data

## ✨ Key Features

### 🎮 Interactive Interface
- **Drag-and-drop pose correction**: Click and drag joint positions directly on video frames
- **Multi-camera support**: View and correct poses across multiple camera angles simultaneously
- **Real-time updates**: See changes reflected immediately in the interface
- **Keyboard shortcuts**: Navigate through frames and errors efficiently

### 🔍 Error Detection System
- **Angle outlier detection**: Identifies sudden changes in joint angles using Savitzky-Golay filtering
- **Length outlier detection**: Detects abnormal segment lengths using statistical analysis
- **Batch error processing**: Process multiple error types simultaneously

### 📹 Video Integration
- **Frame caching**: Optimized performance with intelligent frame caching
- **Error range playback**: Automatically play through detected error ranges

### 📊 Data Management
- **Multiple output formats**: Save corrected data as CSV and HDF5 files
- **Backup and versioning**: Automatic backup of original data so no modification to original data

## 📦 Installation

### Method 1: Standalone Executable (Recommended)

1. **Download the latest release**
   - Navigate to the [Releases](https://github.com/bidaye-lab/dlc_utilities/tree/proofreading_gui) page
   - Download the latest `release.zip`

2. **Install the Application**
   - Right-click `release.zip` in your downloads folder and press "Extract All"
   - Double-click the `install.bat` script to install the application
   - Double-click the `ProofreaderGUI` on your desktop to run

### Method 2: Python Environment Setup 

1. **Clone the repository**
   ```bash
   git clone -b proofreading-gui https://github.com/bidaye-lab/dlc_utilities/tree/proofreading_gui
   cd proofreading_gui
   ```

2. **Create a virtual environment**
   ```bash
   # Using venv (recommended)
   python -m venv .venv
   
   # Activate the environment
   .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify installation**
   ```bash
   python main.py
   ```


### Method 3: Building from Source

1. **Follow Method 2 steps 1-3**

2. **Build the executable**
   ```bash
   python compile_to_exe.py
   ```

3. **Find the executable**
   - Located in `dist/ProofreadingGUI.exe`

## 📁 Expected File Structure

The application is highly adaptive and can work with various folder structures. It automatically detects and adapts to different organizational patterns:

#### Pattern 1: Simple Structure
```
input-folder/
├── anipose/
│   ├── N1/
│   │   ├── pose-3d/
│   │   │   └── {genotype}N1.csv
│   │   └── angles/
│   │       └── {genotype}N1.csv
│   └── N2/
│       ├── pose-3d/
│       │   └── {genotype}N2.csv
│       └── angles/
│           └── {genotype}N2.csv
```

#### Pattern 2: With Type Folders
```
input-folder/
├── anipose/
│   ├── type1/
│   │   └── project/
│   │       ├── N1/
│   │       │   ├── pose-3d/
│   │       │   │   └── {genotype}N1.csv
│   │       │   └── angles/
│   │       │       └── {genotype}N1.csv
│   │       └── N2/
│   └── type2/
│       └── project/
│           ├── N1/
│           │   ├── pose-3d/
│           │   │   └── {genotype}N1.csv
│           │   └── angles/
│           │       └── {genotype}N1.csv
```

#### Pattern 3: With Trials
```
input-folder/
├── anipose/
│   ├── N1/
│   │   ├── trial1/
│   │   │   ├── pose-3d/
│   │   │   │   └── {genotype}N1.csv
│   │   │   └── angles/
│   │   │       └── {genotype}N1.csv
│   │   └── trial2/
│   │       ├── pose-3d/
│   │       │   └── {genotype}N1.csv
│   │       └── angles/
│   │           └── {genotype}N1.csv
```

#### Pattern 4: Complex Structure (Type + Trials)
```
input-folder/
├── anipose/
│   ├── type1/
│   │   └── project/
│   │       ├── N1/
│   │       │   ├── trial1/
│   │       │   │   ├── pose-3d/
│   │       │   │   │   └── {genotype}N1.csv
│   │       │   │   └── angles/
│   │       │   │       └── {genotype}N1.csv
│   │       │   └── trial2/
│   │       │       ├── pose-3d/
│   │       │       │   └── {genotype}N1.csv
│   │       │       └── angles/
│   │       │           └── {genotype}N1.csv
│   │       └── N2/
│   └── type2/
│       └── project/
│           └── N1/
│               └── trial1/
│                   ├── pose-3d/
│                   │   └── {genotype}N1.csv
│                   └── angles/
│                       └── {genotype}N1.csv
```

### Output Structure

The application creates output in two different locations:

### Error Reports and Logs
- **Location**: `input-folder/proofreader-output-{genotype}-N{number}/`
- **Files**:
  - `bunched_outlier_errors.csv`: Detected errors with frame ranges and severity
  - `proofread_progress.csv`: Tracking of which errors have been reviewed
  - `proofreader_log_{date}.log`: Detailed application logs

### Corrected Data
- **Location**: `input-folder/anipose/.../corrected-pose-2d/`
- **Files**:
  - `angles_corrected.csv`: Corrected joint angle data
  - `coords_corrected.csv`: Corrected 3D coordinate data  
  - `corrected-pose-2d.h5`: HDF5 format with all corrected data
  - `{camera}_*.csv/h5`: Individual camera files for further processing

### File Format Requirements

- **{genotype}N{number}.csv**: Joint angle data with columns for each joint (e.g., `L1D_flex`, `R1D_flex`)
- **{genotype}N{number}.csv**: 3D coordinate data with columns for each joint (e.g., `R-F-ThC_x`, `R-F-ThC_y`, `R-F-ThC_z`)
- **Video files**: MP4, AVI, or other OpenCV-compatible formats
- **Camera naming**: Vidos should be named with camera identifiers (i.e. the name must contain the camera letter)

## 🚀 Usage Guide

### 1. Launch the Application

   - Either use `python main.py` or run through the .exe file.

### 2. Project Setup

1. **Select Project Folder**
   - Click "Browse..." to select your input folder
   - Or drag and drop the folder onto the interface

2. **Configure Parameters**
   - **Frame Length**: Number of frames per segment (default: 1400)
   - **Setup Time**: Initial offset for segments (default: 0)

3. **Select Data**
   - Choose the fly number from the dropdown
   - Select the type folder (if applicable)
   - Choose the trial folder (if multiple trials exist)

### 3. Error Detection and Correction

1. **Run Error Detection**
   - Click "Run Correction" to start the error detection process
   - The system will analyze angles and segment lengths for outliers

2. **Navigate Errors**
   - Use "Next Error" and "Previous Error" buttons
   - Or click directly on error entries in the list

3. **Correct Poses**
   - Click and drag joint positions on the video frames
   - Changes are automatically saved

4. **Video Playback**
   - Use play/pause controls for video playback
   - "Play Error Range" automatically plays through detected error frames
   - Navigate frame-by-frame using arrow keys or buttons

### 4. Advanced Features

#### Camera Selection
- Switch between cameras using the camera dropdown
- View multiple camera angles simultaneously
- Each camera shows the same frame with different perspectives

#### Limb Selection
- Select specific limbs for correction using checkboxes
- "Select All" and "Select None" for bulk operations
- Focus on problematic areas while ignoring others

## 🔧 Configuration

### Error Detection Parameters

The error detection system can be customized by modifying `ErrorDetection.py`:

```python
# Angle outlier detection
difference_threshold = 10.0  # Threshold for angle outliers
window_length = 24          # Savitzky-Golay filter window
polyorder = 8              # Polynomial order for smoothing

# Length outlier detection
length_pairs = [("TiTa", "TaG")]  # Segment pairs to analyze
```

### Interface Settings

Modify `constants.py` for:
- Camera mappings
- Joint naming conventions
- Body part configurations

## 🐛 Troubleshooting

### Common Issues

#### 1. "No data files found"
- **Cause**: Incorrect file structure or missing files
- **Solution**: Verify the expected file structure and ensure all needed files exist

#### 2. "Video files not found"
- **Cause**: Video files not in expected location or format
- **Solution**: Check video file paths and names as well as OpenCV-compatible formats

### Getting Help

1. **Check log files** in the output directory for detailed error information
2. **Verify file formats** match expected structure
3. **Report bugs** with log files 

## 🔬 Technical Details

### Error Detection Algorithm

The system uses two main approaches for error detection:

1. **Angle Outlier Detection**:
   - Applies Savitzky-Golay filtering to smooth angle data
   - Calculates difference between raw and smoothed data
   - Identifies frames where difference exceeds threshold
   - Groups consecutive outliers into error bunches

2. **Length Outlier Detection**:
   - Calculates segment lengths from 3D coordinates
   - Computes mean and standard deviation for each segment
   - Identifies frames with z-scores above threshold

### Data Processing Pipeline

1. **Data Loading**: Read CSV files and validate structure
2. **Error Detection**: Apply statistical analysis to identify outliers
3. **User Interface**: Present errors with video context
4. **Correction**: Interactive pose adjustment with real-time feedback
5. **Saving**: Write corrected data to multiple formats
6. **Logging**: Record all operations for reproducibility