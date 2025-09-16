"""
Indicator data file converter script
Author: Alejandro Echeverria
----------------------------------

This script converts an indicator csv data file from the old column format to the new column format used by the latest version of the API service. It attempts to convert all the csv files found in a given path.

Usage:
    python indicator_data_converter.py -i /path/to/input_folder -o /path/to/output_folder

Arguments:
    -i, --input      (required) Path to the input folder containing the source .csv files (old format)
    -o, --output     (required) Path to the output folder to write the output csv files (new format)

Input Requirements:
    - Input files are in csv format containing the following columns:
        subgroup,state,indicator1,indicator2,month,year,country,survey,dist.id,period.id,pred,pred_upper,pred_lower,model,(... additional indicators if any ...)

Output:
    - For each input file, a new csv file is generated in the specified output folder, with the following columns:
            state,indicator1,indicator2,month,year,pred,pred_upper,pred_lower,(... additional indicators if any ...)
    Columns not present in the origin file are ignored.
    Columns not required in the destination file are ignored.
    Additional indicators in the origin file after 'model' column are appended to the destination file.
"""
import os
import argparse
import pandas as pd

def process_csv(input_path, output_path):
    for filename in os.listdir(input_path):
        if filename.endswith('.csv'):
            file_path = os.path.join(input_path, filename)
            df = pd.read_csv(file_path)

            # Get indicator1 and indicator2 column names from header positions 2 and 3
            columns = list(df.columns)
            indicator1 = columns[2] if len(columns) > 2 else None
            indicator2 = columns[3] if len(columns) > 3 else None

            # Build new column list based on available columns
            new_columns = []
            for col in ['state', indicator1, indicator2, 'month', 'year', 'pred', 'pred_upper', 'pred_lower']:
                if col and col in df.columns:
                    new_columns.append(col)

            # Find columns after 'model' and append them
            if 'model' in columns:
                model_idx = columns.index('model')
                extra_columns = columns[model_idx+1:]
                # Only add columns that are not already in new_columns
                extra_columns = [col for col in extra_columns if col not in new_columns]
                new_columns.extend(extra_columns)

            # Select only the columns that exist in the source file and are in the new format
            new_df = df[new_columns]

            # Save to output folder
            out_file = os.path.join(output_path, filename)
            new_df.to_csv(out_file, index=False)
            print(f"Processed {filename} -> {out_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert CSV files to new format.")
    parser.add_argument("-i", "--input", required=True, help="Input folder containing CSV files")
    parser.add_argument("-o", "--output", required=True, help="Output folder for new CSV files")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    process_csv(args.input, args.output)