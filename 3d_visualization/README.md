# Visualize joint coordinates in 3D
The 3D coordinates from Anipose can be visualized using the program [VMD](http://www.ks.uiuc.edu/Research/vmd/),
which is used in chemistry to explore the 3D structures of molecules.

The output from Anipose is a CSV file containing the x, y, and z coordinates for each joint.
Each row corresponds to one movie frame.
The CSV file is converted to an XYZ trajectory file, which is in essence a concatenation of "molecular" structures.
VMD can play these trajectory files.

## Basic usage
Once VMD is set up for the "fly molecule", follow these steps:
- convert the CSV file to an XYZ file using `csv2xyz.py`:
  - activate DLC conda environment
  - navigate to folder containing CSV file
  - run `python path-to-csv2xyz.py 3Dpose.csv` (depending on where you placed `csv2xyz.py` in your files)
- open with VMD

Note that the distances are scaled by a factor of 100 during the conversion from CSV to XYZ for a better representation in VMD.

## Changing the representation
All aspects of VMD can be controlled using the `tcl` scripting language.
The instructions on how to display the "fly molecule" are stored in the `vmd.rc` file (see below).
If you want to change anything about the default representation, it is convenient to edit this file, 
so any newly opened XYZ file will be displayed in the same way.

Note that on windows you need administrator access to edit the `vmd.rc` file at its deault location.
A convenient way would be to edit a copy of the file, say, on the desktop, and copy/paste the updated file confirming administrator access.

The best way to learn the correct commands that need to go into the `vmd.rc` file is to activate logging:
In the VMD main window, click `File` and `Log Tcl commands to console`. 
For any changes that you make through the GUI, the corresponding `tcl` command will appear in the console.

Note that all settings are specific for the "fly molecule"; any other actual molecule will most likely look very strange 
and you would need to restore the original `vmd.rc` file.
Some may argue that the fly looks strange, though.

## Playing trajectories and making movies
VMD can be used to view time-dependent, such as protein folding or chemical reactions 
and it can also render high-quality movies.
The best place to start is the [tutorial](https://www.ks.uiuc.edu/Training/Tutorials/vmd/tutorial-html/node3.html) on the official website.

# Installation
Follow these instructions to install VMD and set it up to display the "fly molecule":
- download VMD 1.9.3 on the official [website](https://www.ks.uiuc.edu/Development/Download/download.cgi?PackageName=VMD)
  - this will require you to create an account (simply email and password)
- install
- replace the file `vmd.rc` in the installation folder with the file from here
  - the default installation folder: `C:\Program Files (x86)\University of Illinois\VMD`
- associate XYZ files with VMD
  - right click on XYZ file (see above)
  - select "Open with..."
  - navigate to installation folder
  - select `vmd.exe`
