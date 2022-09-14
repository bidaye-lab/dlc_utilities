# merge-datasets

merge-datasets performs the efficient concatenation of multiple DeepLabCut-formatted csv files to a single spreadsheet, enabling multiple users to contribute to an individual DeepLabCut project.

<p align="center">
<img src="https://user-images.githubusercontent.com/34531896/190276541-ab22b19c-8455-457a-86f5-04ad74f9c21c.png" width=50% height=50%>
</p>

### Overview

By default, DeepLabCut expects only a single user to annotate all frames within a training dataset. This can quickly become a tedious, difficult process when large datasets are involved. However, the work can be distributed across several users by creating multiple project folders and implementating merge-datasets to combine segregated data.

Our lab enlisted multiple researchers to annotate video frames of a fly walking on an air-supported spherical treadmill. Five joints per leg (with typically 3-4 visible legs per video) were labelled. Separate project folders were created for each leg (the researchers annotated one leg at a time). Following the completion of the annotations, DeepLabCut automatically produced csv files for the labels in each video folder in the project's labeled-data folder. Using these csv files, the merge-datasets script was implemented to automatically merge this segregated data into single csv files to be used as an input training dataset for a DeepLabCut model.

### Tools

1. merge-datasets.ipynb
    - Contains the script to merge annotation labels in separate DeepLabCut project folders
    - Note: Before running all cells, replace any indicated variables with relevant information
  
2. example
    - Contains a sample folder structure for the script, including...
      - a main folder with individual project folders for labeled legs (1-camA-Kate)
      - a folder to which the merged dataset csv files will be output (camA_combined)
      - an empty template csv with all joint names (cam-template)
