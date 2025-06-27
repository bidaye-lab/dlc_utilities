"""
Compilation script for Proofreading GUI Application
Builds a standalone executable using PyInstaller
"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path

def check_pyinstaller():
    """Check if PyInstaller is installed, install if not"""
    try:
        import PyInstaller
        print(f"✓ PyInstaller found: {PyInstaller.__version__}")
        return True
    except ImportError:
        print("PyInstaller not found. Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("✓ PyInstaller installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install PyInstaller: {e}")
            return False

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_packages = [
        'numpy', 'pandas', 'scipy', 'matplotlib', 
        'opencv-python', 'tqdm', 'tables'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✓ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package} - MISSING")
    
    if missing_packages:
        print(f"\nInstalling missing packages: {missing_packages}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
            print("✓ All dependencies installed")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install dependencies: {e}")
            return False
    
    return True

def get_all_site_packages_hiddenimports(venv_path='.venv'):
    import os
    site_packages = os.path.join(venv_path, 'Lib', 'site-packages')
    hiddenimports = set()
    if not os.path.isdir(site_packages):
        print(f"✗ Could not find site-packages at {site_packages}")
        return []
    for entry in os.listdir(site_packages):
        if entry.endswith('.dist-info') or entry.endswith('.egg-info') or entry == '__pycache__':
            continue
        if os.path.isdir(os.path.join(site_packages, entry)):
            hiddenimports.add(entry)
        elif entry.endswith('.py'):
            hiddenimports.add(entry[:-3])
    print(f"✓ Found {len(hiddenimports)} hiddenimports from venv")
    return sorted(hiddenimports)

def create_spec_file():
    """Create a PyInstaller spec file for the application"""
    hiddenimports = get_all_site_packages_hiddenimports()
    # Always add your own modules if not in venv
    hiddenimports += ['constants', 'ErrorDetection']
    # Add essential standard library modules that might be missing
    hiddenimports += [
        'pydoc', 'inspect', 'textwrap', 're', 'copy', 'weakref',
        'functools', 'itertools', 'collections', 'collections.abc',
        'contextlib', 'operator', 'types', 'warnings', 'abc',
        'importlib', 'importlib.util', 'importlib.machinery',
        'importlib.abc', 'importlib.resources', 'threading', 'tempfile',
        'h5py', 'tables', 'pandas.io.formats.format', 'pandas.io.common'
    ]
    # Write the list as a Python list for direct injection as a variable
    hiddenimports_list = [mod for mod in hiddenimports]
    hiddenimports_list_repr = repr(hiddenimports_list)
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

scipy_hiddenimports = collect_submodules('scipy')
scipy_datas = collect_data_files('scipy')
numpy_hiddenimports = collect_submodules('numpy')
numpy_datas = collect_data_files('numpy')
matplotlib_hiddenimports = collect_submodules('matplotlib')
matplotlib_datas = collect_data_files('matplotlib')
pandas_hiddenimports = collect_submodules('pandas')
pandas_datas = collect_data_files('pandas')
h5py_hiddenimports = collect_submodules('h5py')
h5py_datas = collect_data_files('h5py')

hiddenimports_list = {hiddenimports_list_repr}

block_cipher = None

# Collect all data files
datas = list([
    ('PRUI_Icon.ico', '.'),
    ('PRUI_Icon.png', '.'),
    ('constants.py', '.'),
    ('ErrorDetection.py', '.'),
] + scipy_datas + numpy_datas + matplotlib_datas + pandas_datas + h5py_datas)

# Hidden imports for various libraries
hiddenimports = hiddenimports_list + scipy_hiddenimports + numpy_hiddenimports + matplotlib_hiddenimports + pandas_hiddenimports + h5py_hiddenimports

# Exclude unnecessary modules to reduce size
excludes = [
    'tkinter.test'
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ProofreadingGUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='PRUI_Icon.ico',
)
'''
    
    with open('ProofreadingGUI.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("✓ Created PyInstaller spec file with all venv hiddenimports and full scipy/numpy/matplotlib/pandas/h5py support")

def build_executable():
    """Build the executable using PyInstaller"""
    print("\nBuilding executable...")
    
    # Clean previous builds
    if os.path.exists('build'):
        try:
            shutil.rmtree('build')
        except PermissionError:
            print("⚠ Warning: Could not delete 'build' folder (may be in use)")
    
    if os.path.exists('dist'):
        try:
            shutil.rmtree('dist')
        except PermissionError:
            print("⚠ Warning: Could not delete 'dist' folder (may be in use)")
            print("Please close any running instances of ProofreadingGUI.exe and try again")
            return False
    
    # Build using spec file
    try:
        cmd = [sys.executable, "-m", "PyInstaller", "--clean", "ProofreadingGUI.spec"]
        print(f"Running: {' '.join(cmd)}")
        subprocess.check_call(cmd)
        print("✓ Executable built successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Build failed: {e}")
        return False

def main():
    """Main compilation process"""
    print("Proofreading GUI - Executable Compilation")
    print("=" * 50)
    
    # Check current directory
    if not os.path.exists('homepage.py'):
        print("✗ Error: homepage.py not found in current directory")
        print("Please run this script from the project root directory")
        return False
    
    # Step 1: Check and install PyInstaller
    if not check_pyinstaller():
        return False
    
    # Step 2: Check dependencies
    print("\nChecking dependencies...")
    if not check_dependencies():
        return False
    
    # Step 3: Create spec file
    print("\nCreating PyInstaller configuration...")
    create_spec_file()
    
    # Step 4: Build executable
    if not build_executable():
        return False
    

    # Step 5: Show results
    print("\n" + "=" * 50)
    print("COMPILATION COMPLETE!")
    print("=" * 50)
    
    exe_path = os.path.join('dist', 'ProofreadingGUI.exe')
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"✓ Executable created: {exe_path}")
        print(f"✓ Size: {size_mb:.1f} MB")
        print(f"✓ Location: {os.path.abspath('dist')}")
        
        print("\nNext steps:")
        print("1. Test the executable: Run dist/ProofreadingGUI.exe")
        print("2. Install on Windows: Run install.bat as Administrator")
        print("3. Distribute: Share the entire 'dist' folder")
        
        return True
    else:
        print("✗ Executable not found in dist folder")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        print("\nCompilation failed. Please check the error messages above.")
        sys.exit(1)
    else:
        print("\nCompilation successful!")
