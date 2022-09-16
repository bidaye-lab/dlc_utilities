# Fix point in CSV file
Command line tool to replace all coordinates in a DEEPLABCUT CSV file file one value. 

```
usage: dlc_csv_fix_point.py [-h] [-s C] [-n N] csv

Replace all values in a DEEPLABCUT CSV file for training data with one value. This is useful for a point that should
stay fixed. Missing values are conserved. Original file is overwritten, old file is saved as FILENAME_bak

positional arguments:
  csv               Name of the CSV file

optional arguments:
  -h, --help        show this help message and exit
  -s C, --column C  Name of the columns (default: F-TaG)
  -n N, --entry N   Replace values with nth entry (default: 1). To replace with mean of whole column, choose 0
  ```
