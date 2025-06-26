import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import cv2
import numpy as np
import pandas as pd
from matplotlib.text import Annotation
from constants import naming_conversions
import tkinter.font as tkfont
import importlib.util
import sys
import time
from matplotlib import colormaps as mpl_colormaps
from matplotlib.colors import to_rgb, to_hex
from matplotlib import cm
import shutil
from constants import naming_conversions_reverse
import logging
from tqdm import tqdm
from io import StringIO
from datetime import datetime
import traceback
from ErrorDetection import ErrorDetection

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
log_stream = StringIO()
stream_handler = logging.StreamHandler(log_stream)
stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(stream_handler)

# Optional drag-and-drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

class ProofreadingInterface:
    def __init__(self, master):
        self.master = master
        self.master.title("Proofreading GUI")
        self.master.geometry("1200x800")
        
        # Core application variables
        self.folder_path = tk.StringVar()
        self.frame_length = tk.StringVar(value="1400")
        self.setup_time = tk.StringVar(value="0")
        self.genotype = tk.StringVar()
        self.status = tk.StringVar()
        self.fly_number = tk.StringVar()
        self.type_folder = tk.StringVar()
        self.trial_folder = tk.StringVar()
        self.fly_options = []
        self.type_options = []
        self.trial_options = []
        self.angles_file = None
        self.coords_file = None
        self.current_error_index = [0]
        self._pending_pose_edits = set()  # Track (cam, frame) tuples needing save
        
        # Video playback state
        self.current_video_cap = None
        self.current_video_path = None
        self.last_frame_idx = None
        
        self._build_interface()
        
        # Set up variable change callbacks
        self.folder_path.trace_add('write', lambda *a: self.validate_setup())
        self.frame_length.trace_add('write', lambda *a: self.validate_setup())
        self.setup_time.trace_add('write', lambda *a: self.validate_setup())
        self.fly_number.trace_add('write', lambda *a: self.validate_setup())
        self.fly_number.trace_add('write', lambda *a: self.populate_type_options())
        self.type_folder.trace_add('write', lambda *a: self.validate_setup())
        self.type_folder.trace_add('write', lambda *a: self.populate_trial_options())
        self.trial_folder.trace_add('write', lambda *a: self.validate_setup())
        self.master.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_interface(self):
        """Build the main interface with clear organization"""
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Setup tab
        self.setup_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.setup_frame, text="Project Setup")
        
        # Setup scrollable canvas for the setup tab
        self.setup_canvas = tk.Canvas(self.setup_frame, borderwidth=0, highlightthickness=0)
        self.setup_scrollbar = ttk.Scrollbar(self.setup_frame, orient="vertical", command=self.setup_canvas.yview)
        self.setup_canvas.configure(yscrollcommand=self.setup_scrollbar.set)
        self.setup_canvas.pack(side="left", fill="both", expand=True)
        self.setup_scrollbar.pack(side="right", fill="y")
        
        self.setup_scrollable_frame = ttk.Frame(self.setup_canvas)
        self.setup_canvas.create_window((0, 0), window=self.setup_scrollable_frame, anchor="nw", width=self.setup_frame.winfo_reqwidth())
        
        # Bind resizing and scrolling events
        def _on_frame_configure(event):
            self.setup_canvas.configure(scrollregion=self.setup_canvas.bbox("all"))
            self.setup_canvas.itemconfig("all", width=self.setup_canvas.winfo_width())
        self.setup_scrollable_frame.bind("<Configure>", _on_frame_configure)
        
        def _on_canvas_configure(event):
            self.setup_canvas.itemconfig("all", width=event.width)
        self.setup_canvas.bind("<Configure>", _on_canvas_configure)
        
        # Mousewheel scrolling
        def _on_mousewheel(event):
            self.setup_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.setup_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        self._create_setup_tab(parent=self.setup_scrollable_frame)
        
        # Video correction tab (initially disabled)
        self.video_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.video_frame, text="Video Correction", state='disabled')

    def _create_setup_tab(self, parent=None):
        """Create the project setup tab with logical grouping"""
        if parent is None:
            parent = self.setup_frame
            
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        main_frame.columnconfigure(0, weight=1)
        
        # Data Source Section
        data_group = ttk.LabelFrame(main_frame, text="Data Source", padding=15)
        data_group.pack(fill='x', expand=True, pady=(0, 15))
        
        tk.Label(data_group, text="Project Folder:").grid(row=0, column=0, sticky='w', pady=(0, 5))
        
        folder_frame = ttk.Frame(data_group)
        folder_frame.grid(row=1, column=0, sticky='ew', pady=(0, 10))
        data_group.columnconfigure(0, weight=1)
        folder_frame.columnconfigure(0, weight=1)
        
        self.folder_entry = tk.Entry(folder_frame, textvariable=self.folder_path, 
                                    font=('Courier', 10), width=50)
        self.folder_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        browse_btn = tk.Button(folder_frame, text="Browse...", command=self.browse_folder)
        browse_btn.pack(side='right')
        
        # Drag and drop support if available
        if DND_AVAILABLE:
            dnd_label = tk.Label(data_group, text="(or drag folder here)", 
                               relief='groove', height=2, bg='#f5f5f5')
            dnd_label.grid(row=2, column=0, sticky='ew', pady=(0, 5))
            # Check if the label has the required methods for drag and drop
            if hasattr(dnd_label, 'drop_target_register') and hasattr(dnd_label, 'dnd_bind'):
                try:
                    dnd_label.drop_target_register(DND_FILES)  # type: ignore
                    dnd_label.dnd_bind('<<Drop>>', self.on_drop)  # type: ignore
                except Exception as e:
                    logger.warning(f"Failed to set up drag and drop: {e}")
        
        # Analysis Parameters Section
        params_group = ttk.LabelFrame(main_frame, text="Analysis Parameters", padding=15)
        params_group.pack(fill='x', expand=True, pady=(0, 15))
        
        tk.Label(params_group, text="Run Frames (per trial):").grid(row=0, column=0, sticky='w', padx=(0, 10))
        frame_entry = tk.Entry(params_group, textvariable=self.frame_length, width=10)
        frame_entry.grid(row=0, column=1, sticky='w', padx=(0, 5))
        tk.Label(params_group, text="frames").grid(row=0, column=2, sticky='w')
        
        tk.Label(params_group, text="Start Frame (per trial):").grid(row=1, column=0, sticky='w', padx=(0, 10), pady=(5, 0))
        setup_entry = tk.Entry(params_group, textvariable=self.setup_time, width=10)
        setup_entry.grid(row=1, column=1, sticky='w', padx=(0, 5), pady=(5, 0))
        tk.Label(params_group, text="frames").grid(row=1, column=2, sticky='w', pady=(5, 0))
        
        # Advanced options for using all points
        self.use_all_points_var = tk.BooleanVar(value=False)
        use_all_points_group = ttk.LabelFrame(main_frame, text="Use all points for error detection", padding=15)
        use_all_points_group.pack(fill='x', expand=True, pady=(0, 15))
        use_all_points_cb = tk.Checkbutton(
            use_all_points_group,
            text="Check this box to use all available points/angles for error detection (advanced)",
            variable=self.use_all_points_var
        )
        use_all_points_cb.pack(anchor='w')
        
        # Subject Selection Section
        subject_group = ttk.LabelFrame(main_frame, text="Subject Selection", padding=15)
        subject_group.pack(fill='x', expand=True, pady=(0, 15))
        
        tk.Label(subject_group, text="Fly Number:").grid(row=0, column=0, sticky='w', padx=(0, 10))
        self.fly_combobox = ttk.Combobox(subject_group, textvariable=self.fly_number, 
                                        width=15, state='readonly')
        self.fly_combobox.grid(row=0, column=1, sticky='w')
        
        tk.Label(subject_group, text="Type Folder:").grid(row=1, column=0, sticky='w', padx=(0, 10), pady=(5, 0))
        self.type_combobox = ttk.Combobox(subject_group, textvariable=self.type_folder, 
                                          width=15, state='readonly')
        self.type_combobox.grid(row=1, column=1, sticky='w', pady=(5, 0))
        
        tk.Label(subject_group, text="Trial Folder:").grid(row=2, column=0, sticky='w', padx=(0, 10), pady=(5, 0))
        self.trial_combobox = ttk.Combobox(subject_group, textvariable=self.trial_folder, 
                                          width=15, state='readonly')
        self.trial_combobox.grid(row=2, column=1, sticky='w', pady=(5, 0))
        
        tk.Label(subject_group, text="Genotype:").grid(row=3, column=0, sticky='w', padx=(0, 10), pady=(5, 0))
        genotype_label = tk.Label(subject_group, textvariable=self.genotype, 
                                 font=('Courier', 10, 'bold'), fg='blue')
        genotype_label.grid(row=3, column=1, sticky='w', pady=(5, 0))
        
        # Limb Exclusion Section
        exclusion_group = ttk.LabelFrame(main_frame, text="Exclude Limbs from Correction", padding=15)
        exclusion_group.pack(fill='x', expand=True, pady=(0, 15))
        
        # Define limb groupings for UI
        self.limb_defs_ui = {
            'Right Front Leg': ['R-F-ThC', 'R-F-CTr', 'R-F-FTi', 'R-F-TiTa', 'R-F-TaG'],
            'Right Mid Leg': ['R-M-ThC', 'R-M-CTr', 'R-M-FTi', 'R-M-TiTa', 'R-M-TaG'],
            'Right Hind Leg': ['R-H-ThC', 'R-H-CTr', 'R-H-FTi', 'R-H-TiTa', 'R-H-TaG'],
            'Left Front Leg': ['L-F-ThC', 'L-F-CTr', 'L-F-FTi', 'L-F-TiTa', 'L-F-TaG'],
            'Left Mid Leg': ['L-M-ThC', 'L-M-CTr', 'L-M-FTi', 'L-M-TiTa', 'L-M-TaG'],
            'Left Hind Leg': ['L-H-ThC', 'L-H-CTr', 'L-H-FTi', 'L-H-TiTa', 'L-H-TaG'],
            'Wings': ['L-WH', 'R-WH'],
            'Antennae': ['L-antenna', 'R-antenna'],
            'Notum': ['Notum'],
        }
        
        # Create exclusion checkboxes
        self.excluded_limbs = {}
        row = 0
        col = 0
        max_cols = 3
        
        for limb_name, parts in self.limb_defs_ui.items():
            var = tk.BooleanVar(value=False)
            self.excluded_limbs[limb_name] = var
            
            cb = tk.Checkbutton(exclusion_group, text=limb_name, variable=var)
            cb.grid(row=row, column=col, sticky='w', padx=(0, 20), pady=2)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        # Select all/none buttons
        button_frame = ttk.Frame(exclusion_group)
        button_frame.grid(row=row+1, column=0, columnspan=max_cols, pady=(10, 0))
        
        tk.Button(button_frame, text="Select All", 
                 command=self._select_all_limbs).pack(side='left', padx=(0, 10))
        tk.Button(button_frame, text="Select None", 
                 command=self._select_none_limbs).pack(side='left')
        
        # Status label for excluded limbs
        self.exclusion_status = tk.StringVar(value="No limbs excluded")
        status_label = tk.Label(exclusion_group, textvariable=self.exclusion_status, 
                               font=('', 9), fg='darkgreen')
        status_label.grid(row=row+2, column=0, columnspan=max_cols, pady=(5, 0))
        
        # Bind checkboxes to update status
        for var in self.excluded_limbs.values():
            var.trace_add('write', self._update_exclusion_status)
        
        # File Status Section
        status_group = ttk.LabelFrame(main_frame, text="File Status", padding=15)
        status_group.pack(fill='x', expand=True, pady=(0, 15))
        
        self.file_status_text = tk.Text(status_group, height=4, wrap='word', 
                                       font=('Courier', 9), state='disabled')
        self.file_status_text.pack(fill='x')
        
        # Actions Section
        action_group = ttk.LabelFrame(main_frame, text="Actions", padding=15)
        action_group.pack(fill='x', expand=True, pady=(0, 15))
        
        button_frame = ttk.Frame(action_group)
        button_frame.pack(fill='x')
        
        self.validate_btn = tk.Button(button_frame, text="Validate Setup", 
                                     command=self.validate_setup)
        self.validate_btn.pack(side='left', padx=(0, 10))
        
        self.process_btn = tk.Button(button_frame, text="Run Error Detection", 
                                    command=self.run_correction, state='disabled',
                                    font=('', 10, 'bold'))
        self.process_btn.pack(side='left')
        
        # Status Bar
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill='x', expand=True, pady=(15, 0))
        
        tk.Label(status_frame, text="Status:").pack(side='left')
        status_label = tk.Label(status_frame, textvariable=self.status, 
                               font=('', 9), fg='darkgreen')
        status_label.pack(side='left', padx=(5, 0))

    def browse_folder(self):
        """Handle folder browsing"""
        folder = filedialog.askdirectory(title="Select Project Data Folder")
        if folder:
            self.folder_path.set(folder)
            self.populate_fly_options()

    def on_drop(self, event):
        """Handle drag and drop"""
        path = event.data.strip().split()[0].strip('{}')
        if os.path.isdir(path):
            self.folder_path.set(path)
            self.populate_fly_options()
        else:
            self.status.set("Error: Please drop a folder, not a file")

    def populate_fly_options(self):
        """Populate fly options from folder structure"""
        folder = self.folder_path.get()
        anipose_dir = os.path.join(folder, 'anipose')
        fly_folders = []
        checked_folders = []
        
        # Check root anipose directory for N folders first
        if os.path.isdir(anipose_dir):
            for name in os.listdir(anipose_dir):
                full_path = os.path.join(anipose_dir, name)
                checked_folders.append(full_path)
                if name.startswith('N') and os.path.isdir(full_path):
                    fly_folders.append(name[1:])
        
        # If none found, check one level down (type folders)
        if not fly_folders and os.path.isdir(anipose_dir):
            for type_dir in os.listdir(anipose_dir):
                type_path = os.path.join(anipose_dir, type_dir)
                if os.path.isdir(type_path):
                    # Look for project folder within type folder
                    for project_dir in os.listdir(type_path):
                        project_path = os.path.join(type_path, project_dir)
                        if os.path.isdir(project_path):
                            for name in os.listdir(project_path):
                                full_path = os.path.join(project_path, name)
                                checked_folders.append(full_path)
                                if name.startswith('N') and os.path.isdir(full_path):
                                    fly_folders.append(name[1:])
        
        logger.debug(f"Checked folders for fly options: {checked_folders}")
        self.fly_options = sorted(fly_folders, key=lambda x: int(x) if x.isdigit() else x)
        self.fly_combobox['values'] = self.fly_options
        if self.fly_options:
            self.fly_number.set(self.fly_options[0])
            self.populate_type_options()
        else:
            self.fly_number.set('')
            self.type_options = []
            self.type_combobox['values'] = []
            self.type_folder.set('')
            self.trial_options = []
            self.trial_combobox['values'] = []
            self.trial_folder.set('')

    def populate_type_options(self):
        """Populate type folder options for the selected fly number"""
        folder = self.folder_path.get()
        fly_num = self.fly_number.get()
        if not fly_num:
            return
            
        anipose_dir = os.path.join(folder, 'anipose')
        n_folder_name = f'N{fly_num}'
        type_folders = []
        
        # First check if N folder exists directly in anipose (no type folder)
        direct_n_path = os.path.join(anipose_dir, n_folder_name)
        if os.path.isdir(direct_n_path):
            # No type folder needed, add "No Type" option
            type_folders = ["No Type"]
        else:
            # Look for type folders in anipose directory
            if os.path.isdir(anipose_dir):
                for type_dir in os.listdir(anipose_dir):
                    type_path = os.path.join(anipose_dir, type_dir)
                    if os.path.isdir(type_path):
                        # Check if this type folder contains the N folder
                        # Look for project folder within type folder
                        for project_dir in os.listdir(type_path):
                            project_path = os.path.join(type_path, project_dir)
                            if os.path.isdir(project_path):
                                n_folder_path = os.path.join(project_path, n_folder_name)
                                if os.path.isdir(n_folder_path):
                                    type_folders.append(type_dir)
                                    break
        
        if not type_folders:
            type_folders = ["No Type"]
        
        self.type_options = sorted(type_folders)
        self.type_combobox['values'] = self.type_options
        if self.type_options:
            self.type_folder.set(self.type_options[0])
            self.populate_trial_options()
        else:
            self.type_folder.set('')
            self.trial_options = []
            self.trial_combobox['values'] = []
            self.trial_folder.set('')

    def populate_trial_options(self):
        """Populate trial folder options for the selected fly number and type"""
        folder = self.folder_path.get()
        fly_num = self.fly_number.get()
        type_folder = self.type_folder.get()
        if not fly_num:
            return
            
        anipose_dir = os.path.join(folder, 'anipose')
        n_folder_name = f'N{fly_num}'
        trial_folders = []
        n_folder_path = None
        
        # Find the N{number} folder based on type folder selection
        if type_folder and type_folder != "No Type":
            # Look in type_folder/project/N{fly_num}
            type_path = os.path.join(anipose_dir, type_folder)
            if os.path.isdir(type_path):
                for project_dir in os.listdir(type_path):
                    project_path = os.path.join(type_path, project_dir)
                    if os.path.isdir(project_path):
                        n_folder_path = os.path.join(project_path, n_folder_name)
                        if os.path.isdir(n_folder_path):
                            break
        else:
            # Look directly in anipose/N{fly_num}
            n_folder_path = os.path.join(anipose_dir, n_folder_name)
            if not os.path.isdir(n_folder_path):
                n_folder_path = None
        
        # Look for trial folders within the N folder
        if n_folder_path and os.path.isdir(n_folder_path):
            for item in os.listdir(n_folder_path):
                item_path = os.path.join(n_folder_path, item)
                if os.path.isdir(item_path):
                    has_pose3d = os.path.isdir(os.path.join(item_path, 'pose-3d'))
                    has_angles = os.path.isdir(os.path.join(item_path, 'angles'))
                    if has_pose3d or has_angles:
                        trial_folders.append(item)
        
        if not trial_folders:
            trial_folders = ["No Trial"]
        
        self.trial_options = sorted(trial_folders)
        self.trial_combobox['values'] = self.trial_options
        if self.trial_options:
            self.trial_folder.set(self.trial_options[0])
        else:
            self.trial_folder.set('')

    def validate_setup(self):
        """Validate current setup and update status"""
        folder = self.folder_path.get()
        frame_len = self.frame_length.get()
        setup = self.setup_time.get()
        fly_num = self.fly_number.get()
        type_folder = self.type_folder.get()
        trial_folder = self.trial_folder.get()
        
        self.file_status_text.config(state='normal')
        self.file_status_text.delete(1.0, 'end')
        
        if not all([folder, frame_len, setup, fly_num, type_folder, trial_folder]):
            self.file_status_text.insert(1.0, "Please complete all fields above")
            self.file_status_text.config(state='disabled')
            self.status.set("Setup incomplete")
            self.process_btn.config(state='disabled')
            return False
        
        # Validate numeric inputs
        try:
            int(frame_len)
            int(setup)
        except ValueError:
            self.file_status_text.insert(1.0, "Error: Frame length and setup time must be integers")
            self.file_status_text.config(state='disabled')
            self.status.set("Invalid parameters")
            self.process_btn.config(state='disabled')
            return False
        
        # Find required data files
        genotype, coords_path, angles_path = self._find_data_files(folder, fly_num, type_folder, trial_folder)
        
        status_text = []
        if genotype:
            self.genotype.set(genotype)
            status_text.append(f"Genotype detected: {genotype}")
        else:
            status_text.append("Warning: Could not detect genotype")
        
        if coords_path and os.path.isfile(coords_path):
            status_text.append(f"✓ Coordinates file: {os.path.basename(coords_path)}")
            self.coords_file = coords_path
        else:
            status_text.append("✗ Coordinates file not found")
            self.coords_file = None
        
        if angles_path and os.path.isfile(angles_path):
            status_text.append(f"✓ Angles file: {os.path.basename(angles_path)}")
            self.angles_file = angles_path
        else:
            status_text.append("✗ Angles file not found")
            self.angles_file = None
        
        self.file_status_text.insert(1.0, '\n'.join(status_text))
        self.file_status_text.config(state='disabled')
        
        # Enable processing if all files found
        if self.coords_file and self.angles_file and genotype:
            self.status.set("Ready to process")
            self.process_btn.config(state='normal')
            return True
        else:
            self.status.set("Missing required files")
            self.process_btn.config(state='disabled')
            return False

    def _find_data_files(self, folder, fly_num, type_folder, trial_folder):
        """Find and validate data files"""
        genotype = ''
        coords_path = None
        angles_path = None
        anipose_dir = os.path.join(folder, 'anipose')
        
        n_folder_name = f'N{fly_num}'
        found = False
        
        # Construct paths based on type folder selection
        if type_folder and type_folder != "No Type":
            # Look in type_folder/project/N{fly_num}
            type_path = os.path.join(anipose_dir, type_folder)
            if os.path.isdir(type_path):
                for project_dir in os.listdir(type_path):
                    project_path = os.path.join(type_path, project_dir)
                    if os.path.isdir(project_path):
                        base_n_path = os.path.join(project_path, n_folder_name)
                        if os.path.isdir(base_n_path):
                            if trial_folder and trial_folder != "No Trial":
                                pose3d_dir = os.path.join(base_n_path, trial_folder, 'pose-3d')
                                angles_dir = os.path.join(base_n_path, trial_folder, 'angles')
                            else:
                                pose3d_dir = os.path.join(base_n_path, 'pose-3d')
                                angles_dir = os.path.join(base_n_path, 'angles')
                            
                            logger.info(f"Looking for pose3d_dir: {pose3d_dir}")
                            logger.info(f"Looking for angles_dir: {angles_dir}")
                            
                            if os.path.isdir(pose3d_dir):
                                found = True
                                logger.info(f"Found pose3d_dir: {pose3d_dir}")
                                break
        else:
            # Look directly in anipose/N{fly_num}
            base_n_path = os.path.join(anipose_dir, n_folder_name)
            if os.path.isdir(base_n_path):
                if trial_folder and trial_folder != "No Trial":
                    pose3d_dir = os.path.join(base_n_path, trial_folder, 'pose-3d')
                    angles_dir = os.path.join(base_n_path, trial_folder, 'angles')
                else:
                    pose3d_dir = os.path.join(base_n_path, 'pose-3d')
                    angles_dir = os.path.join(base_n_path, 'angles')
                
                logger.info(f"Looking for pose3d_dir: {pose3d_dir}")
                logger.info(f"Looking for angles_dir: {angles_dir}")
                
                if os.path.isdir(pose3d_dir):
                    found = True
                    logger.info(f"Found pose3d_dir: {pose3d_dir}")
        
        if found:
            logger.info(f"Searching for CSV files in: {pose3d_dir}")
            csv_files = [f for f in os.listdir(pose3d_dir) if f.endswith('.csv')]
            logger.info(f"Found CSV files: {csv_files}")
            if len(csv_files) == 1:
                coords_file = csv_files[0]
                coords_path = os.path.join(pose3d_dir, coords_file)
                suffix = f'N{fly_num}.csv'
                logger.info(f"Checking if {coords_file} ends with {suffix}")
                if coords_file.endswith(suffix):
                    genotype = coords_file[:-len(suffix)]
                    angles_path = os.path.join(angles_dir, f'{genotype}N{fly_num}.csv')
                    logger.info(f"Found genotype: {genotype}")
                    logger.info(f"Looking for angles file: {angles_path}")
                    if os.path.isfile(angles_path):
                        logger.info(f"Found angles file: {angles_path}")
                    else:
                        logger.warning(f"Angles file not found: {angles_path}")
                else:
                    logger.warning(f"CSV file {coords_file} does not end with expected suffix {suffix}")
            else:
                logger.warning(f"Expected 1 CSV file, found {len(csv_files)}")
        else:
            logger.error(f"Could not find pose3d directory for N{fly_num}")
        
        logger.info(f"Final results - genotype: {genotype}, coords_path: {coords_path}, angles_path: {angles_path}")
        return genotype, coords_path, angles_path

    def run_correction(self):
        """Run the error detection pipeline"""
        try:
            self.status.set("Processing...")
            self.process_btn.config(state='disabled', text="Processing...")
            self.master.update()
            
            # Validate inputs
            segment_length = int(self.frame_length.get())
            start_segment_setup = int(self.setup_time.get())
            genotype = self.genotype.get()
            
            logger.debug(f"Debug: angles_file = {self.angles_file}")
            logger.debug(f"Debug: coords_file = {self.coords_file}")
            
            if not self.angles_file or not self.coords_file:
                raise ValueError("Required CSV files not found")
            
            # Check file existence and content
            if os.path.isfile(self.angles_file):
                logger.info(f"Angles file exists, size: {os.path.getsize(self.angles_file)} bytes")
                try:
                    with open(self.angles_file, 'r') as f:
                        first_lines = [f.readline() for _ in range(3)]
                    logger.debug(f"First few lines of angles file: {first_lines}")
                except Exception as e:
                    logger.error(f"Error reading angles file: {e}")
            else:
                logger.warning(f"Angles file does not exist: {self.angles_file}")
            
            if os.path.isfile(self.coords_file):
                logger.info(f"Coords file exists, size: {os.path.getsize(self.coords_file)} bytes")
                try:
                    with open(self.coords_file, 'r') as f:
                        first_lines = [f.readline() for _ in range(3)]
                    logger.debug(f"First few lines of coords file: {first_lines}")
                except Exception as e:
                    logger.error(f"Error reading coords file: {e}")
            else:
                logger.warning(f"Coords file does not exist: {self.coords_file}")
            
            # Create output directory
            output_dir = os.path.join(self.folder_path.get(), 
                                    f"proofreader-output-{genotype}-N{self.fly_number.get()}")
            
            # Add type subfolder if a type is selected
            type_folder = self.type_folder.get()
            if type_folder and type_folder != "No Type":
                output_dir = os.path.join(output_dir, type_folder)
            
            # Add trial subfolder if a trial is selected
            trial_folder = self.trial_folder.get()
            if trial_folder and trial_folder != "No Trial":
                output_dir = os.path.join(output_dir, trial_folder)
            
            os.makedirs(output_dir, exist_ok=True)
            
            # Determine angle columns based on user selection
            angle_columns = None
            if self.use_all_points_var.get():
                try:
                    angles_df = pd.read_csv(self.angles_file, engine='python', on_bad_lines='skip')
                    # Use all columns that have a number in their name, but exclude those with 'ThC'
                    angle_columns = [col for col in angles_df.columns if any(char.isdigit() for char in col) and 'A' not in col]
                except Exception as e:
                    logger.error(f"Error reading angles file for all columns: {e}")
                    angle_columns = None
            else:
                # Default columns for error detection
                angle_columns = [
                    'R1D_flex', 'R2D_flex', 'R3D_flex',
                    'L1D_flex', 'L2D_flex', 'L3D_flex'
                ]
            
            if ErrorDetection is None:
                raise ImportError("ErrorDetection module could not be imported")
                
            detector = ErrorDetection(
                angles_path=self.angles_file,
                coords_path=self.coords_file,
                start_segment_setup=start_segment_setup,
                segment_length=segment_length,
                angle_columns=angle_columns
            )
            
            results = detector.run_full_pipeline(output_dir=output_dir)
            
            # Filter out excluded limbs from the error dataframe
            bunched_errors_file = os.path.join(output_dir, "bunched_outlier_errors.csv")
            if os.path.isfile(bunched_errors_file):
                error_df = pd.read_csv(bunched_errors_file)
                
                # Get excluded parts based on selected limbs
                excluded_parts = set()
                for limb_name, var in self.excluded_limbs.items():
                    if var.get():
                        excluded_parts.update(self.limb_defs_ui[limb_name])
                
                # Filter out errors for excluded parts
                if excluded_parts:
                    excluded_outlier_names = set()
                    for part in excluded_parts:
                        # Add all angle names that map to this part
                        for angle_name, seg_name in naming_conversions.items():
                            if seg_name == part:
                                excluded_outlier_names.add(angle_name)
                        # Also add the reverse mapping
                        angle_name = naming_conversions_reverse.get(part, None)
                        if angle_name:
                            excluded_outlier_names.add(angle_name)
                        excluded_outlier_names.add(part)
                    
                    # Filter the dataframe
                    original_count = len(error_df)
                    error_df = error_df[~error_df['Outlier_Name'].isin(list(excluded_outlier_names))]
                    filtered_count = len(error_df)
                    
                    # Save the filtered dataframe
                    error_df.to_csv(bunched_errors_file, index=False)
                    
                    logger.info(f"Filtered out {original_count - filtered_count} errors for excluded limbs: {excluded_parts}")
            
            self.status.set(f"Processing complete! Output saved to: {output_dir}")
            
            # Enable video tab and switch to it
            self.notebook.tab(1, state='normal')
            self.notebook.select(1)
            self._setup_video_tab()
            
            messagebox.showinfo("Processing Complete", 
                              f"Error detection completed successfully!\n\n"
                              f"Results saved to:\n{output_dir}\n\n"
                              f"Switching to Video Correction tab for manual review.")
            
        except Exception as e:
            self.status.set(f"Error: {str(e)}")
            messagebox.showerror("Processing Error", str(e))
        
        finally:
            self.process_btn.config(state='normal', text="Run Error Detection")

    def _setup_video_tab(self):
        """Setup the integrated video correction interface"""
        # Clear existing content
        for widget in self.video_frame.winfo_children():
            widget.destroy()
        
        self._create_video_interface()

    def _create_video_interface(self):
        """Create the video correction interface"""
        # Load constants and error data
        folder = self.folder_path.get()
        fly_num = self.fly_number.get()
        genotype = self.genotype.get()
        output_dir = os.path.join(folder, f"proofreader-output-{genotype}-N{fly_num}")
        
        # Add type subfolder if a type is selected
        type_folder = self.type_folder.get()
        if type_folder and type_folder != "No Type":
            output_dir = os.path.join(output_dir, type_folder)
        
        # Add trial subfolder if a trial is selected
        trial_folder = self.trial_folder.get()
        if trial_folder and trial_folder != "No Trial":
            output_dir = os.path.join(output_dir, trial_folder)
            
        error_file = os.path.join(output_dir, "bunched_outlier_errors.csv")
        progress_file = os.path.join(output_dir, "proofread_progress.csv")
        
        logger.info(f"Looking for error file: {error_file}")
        logger.info(f"Looking for progress file: {progress_file}")
        
        if not os.path.isfile(error_file):
            logger.error(f"Error file not found: {error_file}")
            tk.Label(self.video_frame, text="Error: Could not find error data file", 
                    fg='red', font=('', 12)).pack(pady=20)
            return
        
        # Load error data
        logger.info(f"Loading error data from: {error_file}")
        try:
            # Check if file is empty
            if os.path.getsize(error_file) == 0:
                logger.warning("Error file is empty")
                tk.Label(self.video_frame, text="No errors found in the data", 
                        fg='blue', font=('', 12)).pack(pady=20)
                return
                
            self.error_df = pd.read_csv(error_file)
            logger.info(f"Error data loaded successfully, shape: {self.error_df.shape}")
            
            if self.error_df.empty:
                logger.warning("Error DataFrame is empty")
                tk.Label(self.video_frame, text="No errors found in the data", 
                        fg='blue', font=('', 12)).pack(pady=20)
                return
                
        except pd.errors.EmptyDataError:
            logger.warning("Error file is empty (pandas EmptyDataError)")
            tk.Label(self.video_frame, text="No errors found in the data", 
                    fg='blue', font=('', 12)).pack(pady=20)
            return
        except Exception as e:
            logger.error(f"Error loading error data: {e}")
            tk.Label(self.video_frame, text=f"Error loading error data: {e}", 
                    fg='red', font=('', 12)).pack(pady=20)
            return
        
        # Ensure proofread_progress.csv exists
        logger.info(f"Checking progress file: {progress_file}")
        if not os.path.isfile(progress_file):
            logger.info("Progress file not found, creating new one")
            progress_df = pd.DataFrame({
                'Error': list(range(1, len(self.error_df)+1)),
                'is_completed': [False]*len(self.error_df)
            })
            try:
                progress_df.to_csv(progress_file, index=False)
                logger.info("Progress file created successfully")
            except Exception as e:
                logger.error(f"Error creating progress file: {e}")
        else:
            logger.info("Progress file exists")
        
        # Load progress and find first incomplete error
        start_idx = 0
        try:
            logger.info("Loading progress data")
            progress_df = pd.read_csv(progress_file)
            logger.info(f"Progress data loaded, shape: {progress_df.shape}")
            first_incomplete = progress_df.index[~progress_df['is_completed']].tolist()
            if first_incomplete:
                start_idx = first_incomplete[0]
                logger.info(f"First incomplete error index: {start_idx}")
        except pd.errors.EmptyDataError:
            logger.warning("Progress file is empty (pandas EmptyDataError)")
            progress_df = pd.DataFrame({
                'Error': [],
                'is_completed': []
            })
            try:
                progress_df.to_csv(progress_file, index=False)
                logger.info("Empty progress file created successfully")
            except Exception as e:
                logger.error(f"Error creating empty progress file: {e}")
        except Exception as e:
            logger.error(f"Error loading progress data: {e}")
            traceback.print_exc()
        
        # Load camera constants
        try:
            spec = importlib.util.spec_from_file_location("constants", 
                os.path.join(os.path.dirname(__file__), "constants.py"))
            if spec and spec.loader:
                constants = importlib.util.module_from_spec(spec)
                sys.modules["constants"] = constants
                spec.loader.exec_module(constants)
                self.camera_dict = constants.cameras
            else:
                raise ImportError("Could not load constants")
        except Exception as e:
            tk.Label(self.video_frame, text=f"Error loading camera constants: {e}", 
                    fg='red').pack(pady=20)
            return

        # Find anipose directory robustly
        anipose_root = os.path.join(folder, 'anipose')
        n_folder_name = f'N{fly_num}'
        type_folder = self.type_folder.get()
        trial_folder = self.trial_folder.get()
        anipose_dir = None
        
        # Find the N{number} folder based on type folder selection
        if type_folder and type_folder != "No Type":
            # Look in type_folder/project/N{fly_num}
            type_path = os.path.join(anipose_root, type_folder)
            if os.path.isdir(type_path):
                for project_dir in os.listdir(type_path):
                    project_path = os.path.join(type_path, project_dir)
                    if os.path.isdir(project_path):
                        n_folder_path = os.path.join(project_path, n_folder_name)
                        if os.path.isdir(n_folder_path):
                            # Include trial folder in path if specified
                            if trial_folder and trial_folder != "No Trial":
                                anipose_dir = os.path.join(n_folder_path, trial_folder)
                            else:
                                anipose_dir = n_folder_path
                            break
        else:
            # Look directly in anipose/N{fly_num}
            n_folder_path = os.path.join(anipose_root, n_folder_name)
            if os.path.isdir(n_folder_path):
                # Include trial folder in path if specified
                if trial_folder and trial_folder != "No Trial":
                    anipose_dir = os.path.join(n_folder_path, trial_folder)
                else:
                    anipose_dir = n_folder_path
        
        if anipose_dir is None:
            tk.Label(self.video_frame, text=f"Could not find anipose/project/{n_folder_name}", fg='red').pack(pady=20)
            return
            
        corrected_dir = os.path.join(anipose_dir, 'corrected-pose-2d')
        os.makedirs(corrected_dir, exist_ok=True)
        
        # Copy camera files for editing
        camera_prefixes = set()
        for cam_list in self.camera_dict.values():
            camera_prefixes.update(cam_list)
        logger.info(f"Looking for camera prefixes: {sorted(list(camera_prefixes))}")
        
        # Copy CSV files from main directories
        for subdir in [anipose_dir, os.path.join(anipose_dir, 'Ball')]:
            if os.path.isdir(subdir):
                for f in os.listdir(subdir):
                    if f.lower().endswith('.csv'):
                        for prefix in camera_prefixes:
                            if f.upper().startswith(prefix + '-'):
                                src_path = os.path.join(subdir, f)
                                dst_path = os.path.join(corrected_dir, f)
                                if not os.path.isfile(dst_path):
                                    shutil.copy2(src_path, dst_path)
                                break
        
        # Copy H5 files from pose-2d-filtered directory
        pose2d_filtered_dir = os.path.join(anipose_dir, 'pose-2d-filtered')
        logger.info(f"Looking for H5 files in pose-2d-filtered: {pose2d_filtered_dir}")
        if os.path.isdir(pose2d_filtered_dir):
            logger.info(f"Found pose-2d-filtered directory")
            available_h5s = []
            for f in os.listdir(pose2d_filtered_dir):
                if f.lower().endswith('.h5'):
                    available_h5s.append(f)
                    logger.info(f"Found H5 file in pose-2d-filtered: {f}")
                    # Try multiple matching strategies
                    matched = False
                    for prefix in camera_prefixes:
                        if (f.upper().startswith(prefix + '-') or 
                            prefix.upper() in f.upper() or 
                            f.upper().find(prefix.upper()) != -1):
                            matched = True
                            break
                    
                    if matched:
                        src_path = os.path.join(pose2d_filtered_dir, f)
                        dst_path = os.path.join(corrected_dir, f)
                        logger.info(f"Copying {src_path} to {dst_path}")
                        if not os.path.isfile(dst_path):
                            shutil.copy2(src_path, dst_path)
                            logger.info(f"Successfully copied {f}")
                        else:
                            logger.info(f"File {f} already exists in destination")
            logger.info(f"All available H5 files in pose-2d-filtered: {available_h5s}")
        else:
            logger.warning(f"pose-2d-filtered directory not found at: {pose2d_filtered_dir}")
            # Try alternative locations
            alternative_dirs = [
                os.path.join(anipose_dir, 'pose-2d'),
                os.path.join(anipose_dir, 'pose2d'),
                os.path.join(anipose_dir, 'filtered'),
            ]
            for alt_dir in alternative_dirs:
                if os.path.isdir(alt_dir):
                    logger.info(f"Found alternative directory: {alt_dir}")
                    for f in os.listdir(alt_dir):
                        if f.lower().endswith('.h5'):
                            logger.info(f"Found H5 file in alternative location: {f}")
                            matched = False
                            for prefix in camera_prefixes:
                                if (f.upper().startswith(prefix + '-') or 
                                    prefix.upper() in f.upper() or 
                                    f.upper().find(prefix.upper()) != -1):
                                    matched = True
                                    break
                            
                            if matched:
                                src_path = os.path.join(alt_dir, f)
                                dst_path = os.path.join(corrected_dir, f)
                                logger.info(f"Copying {src_path} to {dst_path}")
                                if not os.path.isfile(dst_path):
                                    shutil.copy2(src_path, dst_path)
                                    logger.info(f"Successfully copied {f}")
                                break
                    break
        
        self.corrected_pose2d_dir = corrected_dir

        # Find video files
        self._find_video_files(folder, fly_num)
        
        # Create interface layout
        self._create_video_layout()

    def _find_video_files(self, folder, fly_num):
        """Find available video files"""
        type_folder = self.type_folder.get()
        trial_folder = self.trial_folder.get()
        
        # Construct video path based on type folder selection
        if type_folder and type_folder != "No Type":
            # Video path: {input_folder}/N{number}/{type_if_there_is_one}/{trial_ifthereisone}/
            n_folder = os.path.join(folder, f'N{fly_num}')
            if type_folder and type_folder != "No Type":
                n_folder = os.path.join(n_folder, type_folder)
            if trial_folder and trial_folder != "No Trial":
                n_folder = os.path.join(n_folder, trial_folder)
        else:
            # Video path: {input_folder}/N{number}/{trial_ifthereisone}/
            n_folder = os.path.join(folder, f'N{fly_num}')
            if trial_folder and trial_folder != "No Trial":
                n_folder = os.path.join(n_folder, trial_folder)
            
        ball_folder = os.path.join(n_folder, 'Ball')
        
        # Get all possible cameras
        all_cameras = set()
        for cam_list in self.camera_dict.values():
            all_cameras.update(cam_list)
        all_cameras = sorted(list(all_cameras))
        
        self.mp4_files = {}
        self.video_frame_counts = {}
        
        for cam in all_cameras:
            found = False
            # Check main folder first
            if os.path.isdir(n_folder):
                for f in os.listdir(n_folder):
                    if f.lower().endswith('.mp4') and f.upper().startswith(cam + '-'):
                        self.mp4_files[cam] = os.path.join(n_folder, f)
                        found = True
                        break
            # Check Ball subfolder if not found and it exists
            if not found and os.path.isdir(ball_folder):
                for f in os.listdir(ball_folder):
                    if f.lower().endswith('.mp4') and f.upper().startswith(cam + '-'):
                        self.mp4_files[cam] = os.path.join(ball_folder, f)
                        break
            
            # Get frame count for video files
            if cam in self.mp4_files:
                try:
                    cap = cv2.VideoCapture(self.mp4_files[cam])
                    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    cap.release()
                    self.video_frame_counts[cam] = total_frames
                except Exception:
                    self.video_frame_counts[cam] = 0
            else:
                self.video_frame_counts[cam] = 0
                
        self.available_cameras = [cam for cam in all_cameras if cam in self.mp4_files]

    def _create_video_layout(self):
        """Create the video interface layout"""
        # Top control panel
        control_panel = ttk.Frame(self.video_frame)
        control_panel.pack(fill='x', padx=10, pady=5)
        
        # Error navigation
        error_frame = ttk.LabelFrame(control_panel, text="Error Navigation", padding=5)
        error_frame.pack(side='left', fill='y', padx=(0, 10))
        
        tk.Button(error_frame, text="< Prev Error", 
                 command=lambda: self.goto_error(-1)).pack(side='left', padx=2)
        
        # Editable error number
        self.error_label_var = tk.StringVar()
        self.error_label = tk.Label(error_frame, textvariable=self.error_label_var, font=('', 10, 'bold'), cursor='hand2')
        self.error_label.pack(side='left', padx=10)
        self.error_label.bind('<Button-1>', self._on_error_label_click)
        self.error_entry = None  # Created on demand
        
        tk.Button(error_frame, text="Next Error >", 
                 command=lambda: self.goto_error(1)).pack(side='left', padx=2)
        
        # Playback controls
        self.play_error_btn = tk.Button(error_frame, text="▶ Play Error", command=self.play_error_range)
        self.play_error_btn.pack(side='left', padx=10)
        self.pause_error_btn = tk.Button(error_frame, text="Pause", command=self.toggle_pause_error, state='disabled')
        self.pause_error_btn.pack(side='left', padx=2)
        
        # Playback state tracking
        self._playing_error = False
        self._paused_error = False
        self._playback_state = None
        
        # Camera and frame controls
        view_frame = ttk.LabelFrame(control_panel, text="View Controls", padding=5)
        view_frame.pack(side='left', fill='y', padx=(0, 10))
        
        tk.Label(view_frame, text="Camera:").grid(row=0, column=0, sticky='w')
        self.camera_var = tk.StringVar(value=self.available_cameras[0] if self.available_cameras else '')
        camera_combo = ttk.Combobox(view_frame, textvariable=self.camera_var, 
                                   values=self.available_cameras, width=8, state='readonly')
        camera_combo.grid(row=0, column=1, padx=5)
        
        tk.Label(view_frame, text="Frame:").grid(row=1, column=0, sticky='w')
        self.frame_var = tk.StringVar(value='0')
        frame_entry = tk.Entry(view_frame, textvariable=self.frame_var, width=8)
        frame_entry.grid(row=1, column=1, padx=5)
        
        tk.Button(view_frame, text="<", command=self.prev_frame).grid(row=1, column=2)
        tk.Button(view_frame, text=">", command=self.next_frame).grid(row=1, column=3)
        
        # Display options
        display_frame = ttk.LabelFrame(control_panel, text="Display Options", padding=5)
        display_frame.pack(side='left', fill='y')
        
        self.show_labels_var = tk.BooleanVar(value=False)
        tk.Checkbutton(display_frame, text="Show labels on hover", 
                      variable=self.show_labels_var).pack(anchor='w')
        
        self.edit_mode_var = tk.BooleanVar(value=True)
        edit_checkbox = tk.Checkbutton(display_frame, text="Edit mode (drag points)", 
                      variable=self.edit_mode_var)
        edit_checkbox.pack(anchor='w')
        edit_checkbox.select()

        # Limb gradient option
        self.limb_gradient_var = tk.BooleanVar(value=False)
        tk.Checkbutton(display_frame, text="Enable limb gradients", 
                      variable=self.limb_gradient_var, command=self.update_display).pack(anchor='w')

        # Auto-mark completion option
        self.auto_mark_completed_var = tk.BooleanVar(value=True)
        self.auto_mark_label = tk.StringVar()
        self._update_auto_mark_label()
        self.auto_mark_checkbox = tk.Checkbutton(
            display_frame,
            textvariable=self.auto_mark_label,
            variable=self.auto_mark_completed_var,
            command=self._on_auto_mark_toggle
        )
        self.auto_mark_checkbox.pack(anchor='w')
        self._set_auto_mark_checkbox_color()

        # Playback options
        cut_playback_frame = ttk.LabelFrame(control_panel, text="Playback Options", padding=5)
        cut_playback_frame.pack(side='left', fill='y', padx=(10,0))
        
        self.cut_playback_at_trial_boundary_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            cut_playback_frame,
            text="Cut playback at trial boundary",
            variable=self.cut_playback_at_trial_boundary_var
        ).pack(anchor='w', pady=(8,0))
        
        self.error_play_margin = tk.IntVar(value=20)
        tk.Label(cut_playback_frame, text="Frames before/after error to play:").pack(anchor='w', pady=(8,0))
        play_margin_entry = tk.Entry(cut_playback_frame, textvariable=self.error_play_margin, width=5)
        play_margin_entry.pack(anchor='w', padx=(10,0))

        # Control sliders
        control_sliders_frame = ttk.LabelFrame(control_panel, text="Control Sliders", padding=5)
        control_sliders_frame.pack(side='left', fill='y', padx=(10,0))
        
        # Playback speed slider
        tk.Label(control_sliders_frame, text="Playback speed:").pack(anchor='w')
        self.playback_speed = tk.IntVar(value=25)
        self.speed_slider = tk.Scale(control_sliders_frame, from_=1, to=50, orient='horizontal', 
                                   variable=self.playback_speed, showvalue=True, length=120)
        self.speed_slider.pack(anchor='w', padx=5)
        
        # Point radius slider
        tk.Label(control_sliders_frame, text="Point size:").pack(anchor='w', pady=(10,0))
        self.point_radius_scale = tk.DoubleVar(value=1.0)
        self.radius_slider = tk.Scale(control_sliders_frame, from_=0.2, to=3.0, resolution=0.05, 
                                    orient='horizontal', variable=self.point_radius_scale, 
                                    showvalue=True, length=120, command=lambda v: self.update_display())
        self.radius_slider.pack(anchor='w', padx=5)

        # Main display area
        display_frame = ttk.Frame(self.video_frame)
        display_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Video display
        video_frame = ttk.LabelFrame(display_frame, text="Video Frame", padding=5)
        video_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        # Create matplotlib figure for video display
        self.fig, self.ax = plt.subplots(figsize=(10, 8))
        self.ax.axis('off')
        self.canvas = FigureCanvasTkAgg(self.fig, master=video_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # Info panel
        info_frame = ttk.LabelFrame(display_frame, text="Information", padding=5)
        info_frame.pack(side='right', fill='y', padx=(5, 0))
        info_frame.config(width=300)
        
        # Current error info
        self.error_info_text = tk.Text(info_frame, height=6, width=35, wrap='word',
                                      font=('Courier', 9))
        self.error_info_text.pack(fill='x', pady=(0, 5))
        
        # File info
        self.file_info_text = tk.Text(info_frame, height=4, width=35, wrap='word',
                                     font=('Courier', 9))
        self.file_info_text.pack(fill='x', pady=(0, 5))
        
        # Recommended cameras
        tk.Label(info_frame, text="Recommended cameras:", font=('', 9, 'bold')).pack(anchor='w')
        self.recommended_text = tk.Text(info_frame, height=5, width=35, wrap='word',
                                       font=('Courier', 9))
        self.recommended_text.pack(fill='x')

        # Color key for limbs
        tk.Label(info_frame, text="Color Key:", font=('', 9, 'bold')).pack(anchor='w', pady=(8,0))
        color_key_frame = tk.Frame(info_frame)
        color_key_frame.pack(fill='x', pady=(0, 5))
        
        limb_colors = {
            'R-F-': 'yellow', 'R-M-': 'green', 'R-H-': 'purple',
            'L-F-': 'cyan', 'L-M-': 'pink', 'L-H-': 'orange',
            'Wings': 'gray', 'Antennae': 'brown', 'Notum': 'black'
        }
        for limb, color in limb_colors.items():
            swatch = tk.Label(color_key_frame, bg=color, width=2, relief='ridge')
            swatch.pack(side='left', padx=(0,2))
            tk.Label(color_key_frame, text=limb, font=('', 8)).pack(side='left', padx=(0,8))

        # Hotkeys explanation
        tk.Label(info_frame, text="Hotkeys:", font=('', 9, 'bold')).pack(anchor='w', pady=(8,0))
        hotkeys_text = tk.Text(info_frame, height=6, width=35, wrap='word', font=('Courier', 8))
        hotkeys_text.pack(fill='x', pady=(0, 5))
        hotkeys_info = """A/D: Previous/Next frame
Q/E: Previous/Next error
S: Next recommended camera
Space: Play/Pause error range
Click error number to edit
Drag points to correct pose"""
        hotkeys_text.insert(1.0, hotkeys_info)
        hotkeys_text.config(state='disabled')

        # Progress bar for save feedback
        self.save_progress = ttk.Progressbar(info_frame, mode='determinate', length=200)
        self.save_progress.pack(fill='x', pady=(5, 0))
        self.save_progress.pack_forget()  # Hide initially
        
        # Set up event handlers
        self.camera_var.trace_add('write', lambda *a: self._on_camera_change())
        self.frame_var.trace_add('write', lambda *a: self.update_display())
        
        # Initialize display state
        self.pose_cache = {}
        self.last_csv_path = {}
        self.scatter = None
        self.scatter_labels = []
        self.hover_annotation = None
        
        # Mouse event handlers
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_motion)
        self.canvas.mpl_connect('button_press_event', self.on_mouse_press)
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_drag)
        self.canvas.mpl_connect('button_release_event', self.on_mouse_release)
        
        # Keyboard event handlers
        self.master.bind('<Key>', self._on_key_press)
        
        # Point movement state
        self.moving_point = {'active': False, 'index': None}
        
        # Load progress and jump to first incomplete error
        start_idx = 0
        try:
            folder = self.folder_path.get()
            fly_num = self.fly_number.get()
            genotype = self.genotype.get()
            output_dir = os.path.join(folder, f"proofreader-output-{genotype}-N{fly_num}")
            
            # Add type subfolder if a type is selected
            type_folder = self.type_folder.get()
            if type_folder and type_folder != "No Type":
                output_dir = os.path.join(output_dir, type_folder)
            
            # Add trial subfolder if a trial is selected
            trial_folder = self.trial_folder.get()
            if trial_folder and trial_folder != "No Trial":
                output_dir = os.path.join(output_dir, trial_folder)
                
            progress_file = os.path.join(output_dir, "proofread_progress.csv")
            if os.path.isfile(progress_file):
                progress_df = pd.read_csv(progress_file)
                first_incomplete = progress_df.index[~progress_df['is_completed']].tolist()
                if first_incomplete:
                    start_idx = first_incomplete[0]
        except Exception:
            pass

        # Go to first error
        if not self.error_df.empty:
            self.goto_error_index(start_idx)
        else:
            self.update_display()

    def goto_error(self, direction):
        """Navigate to previous/next error"""
        if self.error_df.empty:
            return
        
        # Stop any ongoing error playback
        if self._playing_error:
            self._playing_error = False
            self._paused_error = False
            self._playback_state = None
            self.play_error_btn.config(state='normal')
            self.pause_error_btn.config(state='disabled', text='Pause')
        
        # Auto-mark current error as completed when going to next
        if direction == 1 and getattr(self, 'auto_mark_completed_var', None) is not None and self.auto_mark_completed_var.get():
            idx = self.current_error_index[0]
            folder = self.folder_path.get()
            fly_num = self.fly_number.get()
            genotype = self.genotype.get()
            output_dir = os.path.join(folder, f"proofreader-output-{genotype}-N{fly_num}")
            
            # Add type subfolder if a type is selected
            type_folder = self.type_folder.get()
            if type_folder and type_folder != "No Type":
                output_dir = os.path.join(output_dir, type_folder)
            
            # Add trial subfolder if a trial is selected
            trial_folder = self.trial_folder.get()
            if trial_folder and trial_folder != "No Trial":
                output_dir = os.path.join(output_dir, trial_folder)
                
            progress_file = os.path.join(output_dir, "proofread_progress.csv")
            if os.path.isfile(progress_file):
                try:
                    progress_df = pd.read_csv(progress_file)
                    if 0 <= idx < len(progress_df):
                        progress_df.at[idx, 'is_completed'] = True
                        progress_df.to_csv(progress_file, index=False)
                except Exception as e:
                    logger.error(f"Failed to update progress CSV: {e}")
                    
        self._save_pending_pose_edits()
        new_index = max(0, min(len(self.error_df) - 1, self.current_error_index[0] + direction))
        self.goto_error_index(new_index)

    def goto_error_index(self, idx):
        """Go to specific error by index"""
        if self.error_df.empty:
            return
        
        # Stop any ongoing error playback
        if self._playing_error:
            self._playing_error = False
            self._paused_error = False
            self._playback_state = None
            self.play_error_btn.config(state='normal')
            self.pause_error_btn.config(state='disabled', text='Pause')
        
        self._save_pending_pose_edits()
        idx = max(0, min(len(self.error_df) - 1, idx))
        self.current_error_index[0] = idx
        row = self.error_df.iloc[idx]
        part = str(row['Outlier_Name']).split(':')[0].split()[0]
        main_bodypart = naming_conversions.get(part, part)
        cam_letters = self.camera_dict.get(main_bodypart) or self.camera_dict.get(part, [])
        if cam_letters and cam_letters[0] in self.available_cameras:
            self.camera_var.set(cam_letters[0])
        
        # Calculate absolute frame number: start_frame + (N-1)*1400
        trial_num = int(row['N'])
        relative_start_frame = int(row['Start_Frame'])
        absolute_frame = relative_start_frame + (trial_num - 1) * 1400
        self.frame_var.set(str(absolute_frame))
        self.update_display()

    def prev_frame(self):
        """Go to previous frame"""
        try:
            current = int(self.frame_var.get())
            if current > 0:
                self.frame_var.set(str(current - 1))
        except ValueError:
            pass

    def next_frame(self):
        """Go to next frame"""
        try:
            current = int(self.frame_var.get())
            cam = self.camera_var.get()
            max_frame = self.video_frame_counts.get(cam, 1) - 1
            if current < max_frame:
                self.frame_var.set(str(current + 1))
        except ValueError:
            pass

    def update_display(self):
        """Update the video and pose display"""
        cam = self.camera_var.get()
        try:
            frame = int(self.frame_var.get())
        except ValueError:
            frame = 0
        
        # Clear axis
        self.ax.clear()
        self.ax.axis('off')
        
        # Load and display video frame
        mp4_path = self.mp4_files.get(cam)
        img_rgb = None
        if mp4_path and os.path.isfile(mp4_path):
            try:
                # Reuse VideoCapture if possible for performance
                if (self.current_video_cap is None or
                    self.current_video_path != mp4_path):
                    if self.current_video_cap is not None:
                        self.current_video_cap.release()
                    self.current_video_cap = cv2.VideoCapture(mp4_path)
                    self.current_video_path = mp4_path
                    self.last_frame_idx = None
                    
                cap = self.current_video_cap
                # Only seek if not sequential to improve performance
                if self.last_frame_idx is None or abs(frame - self.last_frame_idx) != 1:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
                ret, img = cap.read()
                self.last_frame_idx = frame
                
                if ret and img is not None:
                    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    self.ax.imshow(img_rgb, aspect='auto', 
                                  extent=(0, img_rgb.shape[1], img_rgb.shape[0], 0))
                    self.ax.set_xlim(0, img_rgb.shape[1])
                    self.ax.set_ylim(img_rgb.shape[0], 0)
                else:
                    self.ax.text(0.5, 0.5, f"Frame {frame} not available", 
                               ha='center', va='center', transform=self.ax.transAxes)
            except Exception as e:
                self.ax.text(0.5, 0.5, f"Error loading frame: {e}", 
                           ha='center', va='center', transform=self.ax.transAxes)
        else:
            if self.current_video_cap is not None:
                self.current_video_cap.release()
                self.current_video_cap = None
                self.current_video_path = None
                self.last_frame_idx = None
            self.ax.text(0.5, 0.5, "No video file available", 
                       ha='center', va='center', transform=self.ax.transAxes)
        
        # Display pose data
        self._display_pose_data(cam, frame)
        
        # Update info panels
        self._update_info_panels(cam, frame)
        
        self.canvas.draw()

    def _display_pose_data(self, cam, frame):
        """Display pose estimation points from corrected-pose2d .h5 files"""
        folder = self.folder_path.get()
        fly_num = self.fly_number.get()
        type_folder = self.type_folder.get()
        trial_folder = self.trial_folder.get()
        
        # Find correct anipose directory
        anipose_root = os.path.join(folder, 'anipose')
        n_folder_name = f'N{fly_num}'
        anipose_dir = None
        
        # Find the N{number} folder based on type folder selection
        if type_folder and type_folder != "No Type":
            # Look in type_folder/project/N{fly_num}
            type_path = os.path.join(anipose_root, type_folder)
            if os.path.isdir(type_path):
                for project_dir in os.listdir(type_path):
                    project_path = os.path.join(type_path, project_dir)
                    if os.path.isdir(project_path):
                        n_folder_path = os.path.join(project_path, n_folder_name)
                        if os.path.isdir(n_folder_path):
                            # Include trial folder in path if specified
                            if trial_folder and trial_folder != "No Trial":
                                anipose_dir = os.path.join(n_folder_path, trial_folder)
                            else:
                                anipose_dir = n_folder_path
                            break
        else:
            # Look directly in anipose/N{fly_num}
            n_folder_path = os.path.join(anipose_root, n_folder_name)
            if os.path.isdir(n_folder_path):
                # Include trial folder in path if specified
                if trial_folder and trial_folder != "No Trial":
                    anipose_dir = os.path.join(n_folder_path, trial_folder)
                else:
                    anipose_dir = n_folder_path
                    
        if anipose_dir is None:
            logger.error(f"Could not find anipose directory for N{fly_num}")
            return
        
        # Load pose data from corrected directory
        corrected_dir = os.path.join(anipose_dir, 'corrected-pose-2d')
        h5_path = None
        available_h5s = []
        
        if os.path.isdir(corrected_dir):
            for f in os.listdir(corrected_dir):
                if f.lower().endswith('.h5'):
                    available_h5s.append(f)
                    # Match camera to H5 file: Genotype-{camera letter}.h5
                    if f.upper().endswith(f'-{cam}.h5'.upper()):
                        h5_path = os.path.join(corrected_dir, f)
                        break
        else:
            logger.error(f"corrected-pose-2d directory not found at: {corrected_dir}")
        
        if not h5_path:
            logger.warning(f"No pose H5 found for camera {cam} in {corrected_dir}. Available: {available_h5s}")
            return
        
        # Load pose data with caching
        if cam not in self.pose_cache or self.last_csv_path.get(cam) != h5_path:
            try:
                self.pose_cache[cam] = pd.read_hdf(h5_path)
                self.last_csv_path[cam] = h5_path
                
                # Set all ThC points to likelihood = 1
                pose_df = self.pose_cache[cam]
                for scorer in pose_df.columns.levels[0]:  # Iterate through all scorers
                    for bodypart in pose_df.columns.levels[1]:  # Iterate through all bodyparts
                        if 'ThC' in bodypart and (scorer, bodypart, 'likelihood') in pose_df.columns:
                            pose_df[(scorer, bodypart, 'likelihood')] = 1.0
                            logger.info(f"Set {scorer}-{bodypart} likelihood to 1.0 for camera {cam}")
                
            except Exception as e:
                logger.error(f"Failed to load pose H5 {h5_path}: {e}")
                self.pose_cache[cam] = None
                return
                
        pose_df = self.pose_cache.get(cam)
        if pose_df is None or frame >= len(pose_df):
            return
        
        # Define limb groupings and colors
        limb_defs = {
            'R-F-': ['ThC', 'CTr', 'FTi', 'TiTa', 'TaG'],
            'R-M-': ['ThC', 'CTr', 'FTi', 'TiTa', 'TaG'],
            'R-H-': ['ThC', 'CTr', 'FTi', 'TiTa', 'TaG'],
            'L-F-': ['ThC', 'CTr', 'FTi', 'TiTa', 'TaG'],
            'L-M-': ['ThC', 'CTr', 'FTi', 'TiTa', 'TaG'],
            'L-H-': ['ThC', 'CTr', 'FTi', 'TiTa', 'TaG'],
            'Wings': ['L-WH', 'R-WH'],
            'Antennae': ['L-antenna', 'R-antenna'],
            'Notum': ['Notum'],
        }
        
        limb_colors = {
            'R-F-': 'yellow', 'R-M-': 'green', 'R-H-': 'purple',
            'L-F-': 'cyan', 'L-M-': 'pink', 'L-H-': 'orange',
            'Wings': 'gray', 'Antennae': 'brown', 'Notum': 'black'
        }
        
        # Create gradient colors for limbs if enabled
        def make_gradient(base_color, n=5):
            base = np.array(to_rgb(base_color))
            dark = base * 0.4
            light = base + (1.0 - base) * 0.7
            colors = [to_hex(tuple((dark + (light - dark) * (i/(n-1))).tolist())) for i in range(n)]
            return colors
        
        leg_base_colors = {
            'R-F-': 'yellow', 'R-M-': 'green', 'R-H-': 'purple',
            'L-F-': 'cyan', 'L-M-': 'pink', 'L-H-': 'orange',
        }
        leg_gradients = {k: make_gradient(v) for k, v in leg_base_colors.items()}
        
        row = pose_df.iloc[frame]
        points = []
        labels = []
        colors = []
        sizes = []
        
        # Identify current error's main bodypart for highlighting
        main_bodypart = None
        leg_prefix = None
        if not self.error_df.empty:
            idx = self.current_error_index[0]
            error_row = self.error_df.iloc[idx]
            outlier_name = str(error_row['Outlier_Name']).split(':')[0].split()[0]
            main_bodypart = naming_conversions.get(outlier_name, outlier_name)
            if '-' in main_bodypart:
                leg_prefix = '-'.join(main_bodypart.split('-')[:2]) + '-'
        
        # Process each bodypart in the pose data
        for bodypart in pose_df.columns.levels[1]:  # Bodyparts are at level 1
            # Check if all required coordinates exist
            has_all_coords = True
            for coord in ['x', 'y', 'likelihood']:
                found_coord = False
                for scorer in pose_df.columns.levels[0]:  # Scorers at level 0
                    if (scorer, bodypart, coord) in pose_df.columns:
                        found_coord = True
                        break
                if not found_coord:
                    has_all_coords = False
                    break
            
            if not has_all_coords:
                continue
            
            # Get data from first available scorer
            scorer = pose_df.columns.levels[0][0]
            x = row[(scorer, bodypart, 'x')]
            y = row[(scorer, bodypart, 'y')]
            likelihood = row[(scorer, bodypart, 'likelihood')]
            
            # Skip low-confidence points
            if not (np.isfinite(x) and np.isfinite(y) and likelihood > 0.1):
                continue
            
            label = bodypart
            points.append((x, y))
            labels.append(label)
            
            # Determine limb prefix for coloring
            limb_prefix = None
            for prefix in limb_defs:
                if label.startswith(prefix):
                    limb_prefix = prefix
                    break
            
            # Apply gradient coloring if enabled
            if self.limb_gradient_var.get() and limb_prefix in leg_gradients and limb_prefix in limb_defs:
                part_list = limb_defs[limb_prefix]
                segment = label[len(limb_prefix):] if label.startswith(limb_prefix) else label
                if segment in part_list:
                    part_idx = part_list.index(segment)
                    color = leg_gradients[limb_prefix][part_idx]
                else:
                    color = limb_colors.get(limb_prefix or label, 'red')
            else:
                color = limb_colors.get(limb_prefix or label, 'red')
            
            # Size points based on relevance to current error
            scale = self.point_radius_scale.get() if hasattr(self, 'point_radius_scale') else 1.0
            if main_bodypart and label == main_bodypart:
                colors.append('red')
                sizes.append(120 * scale)
            elif leg_prefix and label.startswith(leg_prefix):
                colors.append(color)
                sizes.append(80 * scale)
            else:
                colors.append(color)
                sizes.append(40 * scale)
        
        # Display the points
        if points:
            points = np.array(points)
            self.scatter = self.ax.scatter(points[:,0], points[:,1], 
                                         c=colors, s=sizes, picker=True, 
                                         edgecolors='black', linewidths=1, alpha=0.8)
            self.scatter_labels = labels

    def _update_info_panels(self, cam, frame):
        """Update information panels"""
        # Current error info
        self.error_info_text.delete(1.0, 'end')
        if not self.error_df.empty:
            idx = self.current_error_index[0]
            row = self.error_df.iloc[idx]
            error_info = f"Error {idx+1}/{len(self.error_df)}\n"
            error_info += f"Bodypart: {row['Outlier_Name']}\n"
            error_info += f"Trial: N{row['N']}\n"
            error_info += f"Frames: {row['Start_Frame']}-{row['End_Frame']}\n"
            error_info += f"Max Error: {row['Max_Error']:.2f}\n"
            error_info += f"Avg Error: {row['Avg_Error']:.2f}"
            self.error_info_text.insert(1.0, error_info)
            self.error_label_var.set(f"Error {idx+1}/{len(self.error_df)}: {row['Outlier_Name']}")
        else:
            self.error_info_text.insert(1.0, "No errors found")
            self.error_label_var.set("No errors")
        
        # File info
        self.file_info_text.delete(1.0, 'end')
        mp4_path = self.mp4_files.get(cam, "Not found")
        total_frames = self.video_frame_counts.get(cam, 0)
        
        file_info = f"Camera: {cam}\n"
        file_info += f"Frame: {frame}/{total_frames-1 if total_frames > 0 else 0}\n"
        file_info += f"Video: {os.path.basename(mp4_path) if mp4_path != 'Not found' else 'Not found'}"
        
        self.file_info_text.insert(1.0, file_info)
        
        # Recommended cameras
        self.recommended_text.delete(1.0, 'end')
        if not self.error_df.empty:
            idx = self.current_error_index[0]
            row = self.error_df.iloc[idx]
            part = str(row['Outlier_Name']).split(':')[0].split()[0]
            # Try both mapping directions
            main_bodypart = naming_conversions.get(part, part)
            if main_bodypart == part:
                main_bodypart = naming_conversions_reverse.get(part, part)
            cams = self.camera_dict.get(main_bodypart) or self.camera_dict.get(part, [])
            if cams:
                rec_text = "Best views:\n" + "\n".join(f"• {c}" for c in cams[:3])
            else:
                rec_text = "No specific recommendations"
            self.recommended_text.insert(1.0, rec_text)

    def on_mouse_motion(self, event):
        """Handle mouse motion for hover labels and dragging"""
        # Handle hover labels
        if (self.show_labels_var.get() and self.scatter is not None and 
            hasattr(self.scatter, 'contains') and event.inaxes == self.ax):
            
            cont, ind = self.scatter.contains(event)
            if cont and 'ind' in ind and len(ind['ind']) > 0:
                i = int(ind['ind'][0])
                if i < len(self.scatter_labels):
                    label = self.scatter_labels[i]
                    offsets = self.scatter.get_offsets()
                    if not isinstance(offsets, np.ndarray):
                        offsets = np.array(offsets)
                    
                    x, y = float(offsets[i][0]), float(offsets[i][1])
                    
                    if self.hover_annotation:
                        try:
                            self.hover_annotation.remove()
                        except:
                            pass
                    
                    self.hover_annotation = self.ax.annotate(
                        label, (x, y), xytext=(10, 10), textcoords='offset points',
                        bbox=dict(boxstyle="round", fc="yellow", alpha=0.8),
                        arrowprops=dict(arrowstyle="->", color='black'),
                        fontsize=10, zorder=1000
                    )
                    self.canvas.draw_idle()
            else:
                if self.hover_annotation:
                    try:
                        self.hover_annotation.remove()
                        self.hover_annotation = None
                        self.canvas.draw_idle()
                    except:
                        pass
        
        # Handle point dragging
        if (self.edit_mode_var.get() and self.moving_point['active'] and 
            event.xdata is not None and event.ydata is not None):
            self._drag_point(event.xdata, event.ydata)

    def on_mouse_press(self, event):
        """Handle mouse press for point selection"""
        if (self.edit_mode_var.get() and self.scatter is not None and 
            hasattr(self.scatter, 'contains') and event.inaxes == self.ax):
            
            cont, ind = self.scatter.contains(event)
            if cont and 'ind' in ind and len(ind['ind']) > 0:
                i = int(ind['ind'][0])
                self.moving_point['active'] = True
                self.moving_point['index'] = i

    def on_mouse_drag(self, event):
        """Handle mouse dragging - processed in on_mouse_motion for smoother interaction"""
        pass

    def on_mouse_release(self, event):
        """Handle mouse release to save point changes"""
        if (self.edit_mode_var.get() and self.moving_point['active'] and 
            event.xdata is not None and event.ydata is not None):
            
            self._save_point_edit(event.xdata, event.ydata)
        
        self.moving_point['active'] = False
        self.moving_point['index'] = None

    def _drag_point(self, x, y):
        """Update point position during drag"""
        if (self.scatter is None or self.moving_point['index'] is None or 
            self.moving_point['index'] >= len(self.scatter_labels)):
            return
        
        try:
            i = self.moving_point['index']
            offsets = self.scatter.get_offsets()
            if not isinstance(offsets, np.ndarray):
                offsets = np.array(offsets)
            
            offsets[i][0] = x
            offsets[i][1] = y
            self.scatter.set_offsets(offsets)
            self.canvas.draw_idle()
        except Exception:
            pass

    def _save_point_edit(self, x, y):
        """Update edited point in memory, mark for later save"""
        if (self.moving_point['index'] is None or 
            self.moving_point['index'] >= len(self.scatter_labels)):
            return
            
        try:
            i = self.moving_point['index']
            label = self.scatter_labels[i]
            cam = self.camera_var.get()
            frame = int(self.frame_var.get())
            h5_path = self.last_csv_path.get(cam)
            pose_df = self.pose_cache.get(cam)
            
            if not h5_path or pose_df is None:
                return
            
            # Update coordinates in the H5 dataframe
            scorer = pose_df.columns.levels[0][0]  # Get first scorer
            if (scorer, label, 'x') in pose_df.columns:
                pose_df.at[frame, (scorer, label, 'x')] = x
            if (scorer, label, 'y') in pose_df.columns:
                pose_df.at[frame, (scorer, label, 'y')] = y
            
            self._pending_pose_edits.add(cam)
            logger.info(f"Updated {label} position at frame {frame} for camera {cam}")
            self.status.set(f"Updated {label} position at frame {frame} (not yet saved)")
            
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not update point edit: {e}")

    def _show_save_progress(self):
        """Show progress bar for save operations"""
        self.save_progress.config(mode='determinate', maximum=100, value=0)
        self.save_progress.pack(fill='x', pady=(5, 0))
        self.save_progress.update_idletasks()
        self.master.update_idletasks()

    def _update_save_progress(self, value, stage_text=""):
        """Update progress bar with current value and stage text"""
        self.save_progress.config(value=value)
        if stage_text:
            self.status.set(f"Saving: {stage_text}")
        self.save_progress.update_idletasks()
        self.master.update_idletasks()

    def _hide_save_progress(self):
        """Hide progress bar after save completion"""
        self.save_progress.pack_forget()
        self.save_progress.update_idletasks()
        self.status.set("Ready")

    def _save_pending_pose_edits(self):
        """Save all pending pose edits to disk with progress feedback"""
        if not self._pending_pose_edits:
            return
        
        self._show_save_progress()
        total_cameras = len(self._pending_pose_edits)
        current_camera = 0
        
        for cam in tqdm(list(self._pending_pose_edits), desc="Saving pose edits", unit="camera"):
            current_camera += 1
            progress_per_camera = 100 // total_cameras
            start_progress = (current_camera - 1) * progress_per_camera
            
            self._update_save_progress(start_progress, f"Preparing to save {cam}")
            
            pose_df = self.pose_cache.get(cam)
            h5_path = self.last_csv_path.get(cam)
            
            # Only save to corrected-pose-2d directory
            if pose_df is not None and h5_path and 'corrected-pose-2d' in h5_path:
                try:
                    self._update_save_progress(start_progress + progress_per_camera // 3, f"Saving H5 file for {cam}")
                    logger.info(f"Saving H5 file: {h5_path}")
                    pose_df.to_hdf(h5_path, key='df', mode='w')
                    
                    self._update_save_progress(start_progress + 2 * progress_per_camera // 3, f"Saving CSV file for {cam}")
                    csv_path = h5_path.replace('.h5', '.csv')
                    logger.info(f"Saving CSV file: {csv_path}")
                    pose_df.to_csv(csv_path, index=False)
                    
                    self._update_save_progress(start_progress + progress_per_camera, f"Completed saving {cam}")
                    logger.info(f"Saved edits for {cam} to both H5 and CSV formats")
                    
                except Exception as e:
                    logger.error(f"Failed to save edits for {cam}: {e}")
                    self.status.set(f"Error saving {cam}: {e}")
            else:
                logger.warning(f"Not saving - conditions not met: pose_df={pose_df is not None}, h5_path={h5_path}, corrected-pose-2d in path={'corrected-pose-2d' in h5_path if h5_path else False}")
            
            self._pending_pose_edits.discard(cam)
        
        self._update_save_progress(100, "Save completed")
        self.master.after(500, self._hide_save_progress)

    def _on_camera_change(self, *args):
        """Handle camera selection change"""
        self._save_pending_pose_edits()
        self.update_display()

    def _on_close(self):
        """Handle application close event"""
        self._save_pending_pose_edits()
        if self.current_video_cap is not None:
            self.current_video_cap.release()
            self.current_video_cap = None
            self.current_video_path = None
            self.last_frame_idx = None
        # Save log file to proofreader-output dir
        try:
            folder = self.folder_path.get()
            fly_num = self.fly_number.get()
            genotype = self.genotype.get()
            if folder and fly_num and genotype:
                output_dir = os.path.join(folder, f"proofreader-output-{genotype}-N{fly_num}")
                
                # Add type subfolder if a type is selected
                type_folder = self.type_folder.get()
                if type_folder and type_folder != "No Type":
                    output_dir = os.path.join(output_dir, type_folder)
                
                # Add trial subfolder if a trial is selected
                trial_folder = self.trial_folder.get()
                if trial_folder and trial_folder != "No Trial":
                    output_dir = os.path.join(output_dir, trial_folder)
                    
                os.makedirs(output_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                log_path = os.path.join(output_dir, f"proofreader_log_{timestamp}.log")
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write(log_stream.getvalue())
                logger.info(f"Log file saved to {log_path}")
        except Exception as e:
            logger.error(f"Failed to save log file: {e}")
        self.master.destroy()

    def play_error_range(self):
        """Play video from N frames before error start to N after error end"""
        if self.error_df.empty or self._playing_error:
            return
            
        idx = self.current_error_index[0]
        row = self.error_df.iloc[idx]
        
        try:
            # Calculate absolute frame numbers
            trial_num = int(row['N'])
            relative_start = int(row['Start_Frame'])
            relative_end = int(row['End_Frame'])
            absolute_start = relative_start + (trial_num - 1) * 1400
            absolute_end = relative_end + (trial_num - 1) * 1400
            trial_first_frame = (trial_num - 1) * 1400
        except Exception:
            return
            
        cam = self.camera_var.get()
        total_frames = self.video_frame_counts.get(cam, 0)
        margin = self.error_play_margin.get() if hasattr(self, 'error_play_margin') else 20
        
        # Respect trial boundary option
        if hasattr(self, 'cut_playback_at_trial_boundary_var') and self.cut_playback_at_trial_boundary_var.get():
            play_start = max(trial_first_frame, absolute_start - margin)
        else:
            play_start = max(0, absolute_start - margin)
            
        play_end = min(total_frames - 1, absolute_end + margin)
        fps = self.playback_speed.get()
        delay = int(1000 / max(1, fps))
        
        self._playing_error = True
        self._paused_error = False
        self._playback_state = None
        self.play_error_btn.config(state='disabled')
        self.pause_error_btn.config(state='normal', text='Pause')
        
        # Store original edit mode and disable during playback
        self._original_edit_mode = self.edit_mode_var.get()
        self.edit_mode_var.set(False)
        
        self._play_error_frame_step(play_start, play_end, cam, delay)

    def toggle_pause_error(self):
        """Toggle pause/resume for error playback"""
        if not self._playing_error:
            return
            
        if not self._paused_error:
            # Pause playback
            self._paused_error = True
            self.pause_error_btn.config(text='Resume')
            # Restore edit mode when paused
            if hasattr(self, '_original_edit_mode'):
                self.edit_mode_var.set(self._original_edit_mode)
        else:
            # Resume playback
            self._paused_error = False
            self.pause_error_btn.config(text='Pause')
            # Disable edit mode during playback
            self.edit_mode_var.set(False)
            if self._playback_state:
                current, end, cam = self._playback_state
                fps = self.playback_speed.get()
                delay = int(1000 / max(1, fps))
                self._play_error_frame_step(current, end, cam, delay)

    def _play_error_frame_step(self, current, end, cam, delay):
        """Single step in error playback animation"""
        if not self._playing_error:
            self.play_error_btn.config(state='normal')
            self.pause_error_btn.config(state='disabled', text='Pause')
            # Restore original edit mode
            if hasattr(self, '_original_edit_mode'):
                self.edit_mode_var.set(self._original_edit_mode)
            return
            
        if self._paused_error:
            self._playback_state = (current, end, cam)
            return
            
        self._playback_state = None
        self.frame_var.set(str(current))
        self.master.update_idletasks()
        self.canvas.get_tk_widget().update_idletasks()
        
        if current < end and self.camera_var.get() == cam:
            self.master.after(delay, lambda: self._play_error_frame_step(current + 1, end, cam, delay))
        else:
            self._playing_error = False
            self.play_error_btn.config(state='normal')
            self.pause_error_btn.config(state='disabled', text='Pause')
            # Restore original edit mode
            if hasattr(self, '_original_edit_mode'):
                self.edit_mode_var.set(self._original_edit_mode)

    def _on_auto_mark_toggle(self):
        """Handle auto-mark completion toggle"""
        self._update_auto_mark_label()
        self._set_auto_mark_checkbox_color()

    def _update_auto_mark_label(self):
        """Update auto-mark label text"""
        if self.auto_mark_completed_var.get():
            self.auto_mark_label.set("Auto-mark next error as completed (recommended)")
        else:
            self.auto_mark_label.set("Auto-mark next error as completed (recommended)")

    def _set_auto_mark_checkbox_color(self):
        """Set checkbox color based on state"""
        if self.auto_mark_completed_var.get():
            self.auto_mark_checkbox.config(fg='black')
        else:
            self.auto_mark_checkbox.config(fg='red')

    def _on_error_label_click(self, event):
        """Handle click on error label to enable editing"""
        if self.error_entry is not None:
            return  # Already editing
            
        idx = self.current_error_index[0] if self.current_error_index else 0
        self.error_entry_var = tk.StringVar(value=str(idx+1))
        self.error_entry = tk.Entry(self.error_label.master, textvariable=self.error_entry_var, 
                                   width=6, font=('', 10, 'bold'))
        self.error_entry.pack(side='left', padx=10)
        self.error_label.pack_forget()
        self.error_entry.focus_set()
        self.error_entry.bind('<Return>', self._on_error_entry_commit)
        self.error_entry.bind('<FocusOut>', self._on_error_entry_commit)

    def _on_error_entry_commit(self, event):
        """Handle error number entry commit"""
        try:
            val = int(self.error_entry_var.get())
            if 1 <= val <= len(self.error_df):
                self.goto_error_index(val-1)
        except Exception:
            pass
            
        if self.error_entry is not None:
            self.error_entry.pack_forget()
            self.error_entry = None
        self.error_label.pack(side='left', padx=10)

    def _on_key_press(self, event):
        """Handle keyboard hotkeys"""
        if event.char == 'a':
            self.prev_frame()
        elif event.char == 'd':
            self.next_frame()
        elif event.char == 'e':
            self.goto_error(1)  # Next error
        elif event.char == 'q':
            self.goto_error(-1)  # Previous error
        elif event.char == 's':
            self.next_recommended_camera()
        elif event.keysym == 'space':
            # Toggle play/pause for error playback
            if self._playing_error:
                self.toggle_pause_error()
            else:
                self.play_error_range()

    def next_recommended_camera(self):
        """Cycle to the next recommended camera for the current error"""
        if self.error_df.empty:
            return
        
        # Get current error's recommended cameras
        idx = self.current_error_index[0]
        row = self.error_df.iloc[idx]
        part = str(row['Outlier_Name']).split(':')[0].split()[0]
        # Try both mapping directions
        main_bodypart = naming_conversions.get(part, part)
        if main_bodypart == part:
            main_bodypart = naming_conversions_reverse.get(part, part)
        recommended_cams = self.camera_dict.get(main_bodypart) or self.camera_dict.get(part, [])
        
        if not recommended_cams:
            return
        
        # Filter to only available cameras
        available_recommended = [cam for cam in recommended_cams if cam in self.available_cameras]
        
        if not available_recommended:
            return
        
        # Find current camera in recommended list
        current_cam = self.camera_var.get()
        try:
            current_index = available_recommended.index(current_cam)
            next_index = (current_index + 1) % len(available_recommended)
        except ValueError:
            # Current camera not in recommended list, start with first
            next_index = 0
        
        # Switch to next recommended camera
        next_cam = available_recommended[next_index]
        self.camera_var.set(next_cam)
        self.status.set(f"Switched to recommended camera: {next_cam}")

    def _select_all_limbs(self):
        """Select all limbs for exclusion"""
        for var in self.excluded_limbs.values():
            var.set(True)

    def _select_none_limbs(self):
        """Select no limbs for exclusion"""
        for var in self.excluded_limbs.values():
            var.set(False)

    def _update_exclusion_status(self, *args):
        """Update the exclusion status label"""
        excluded_limbs = [limb for limb, var in self.excluded_limbs.items() if var.get()]
        if excluded_limbs:
            self.exclusion_status.set(f"Excluded limbs: {', '.join(excluded_limbs)}")
        else:
            self.exclusion_status.set("No limbs excluded")

def main():
    """Main application entry point"""
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    
    app = ProofreadingInterface(root)
    root.mainloop()
