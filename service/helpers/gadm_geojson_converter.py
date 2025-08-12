"""
GeoJSON Converter Script
Author: Emily Driano
----------------------------------

This script converts a directory of GADM formatted GeoJSON files (admin levels 0–2) into the GeoJSON format expected by
the service, and then consequently serializes the .json files into .shp.pickle files. Each output file contains a dictionary
of features keyed by hierarchical IDs, optionally scoped to a continent.

Usage:
    python gadm_geojson_converter.py -i /path/to/input_geojsons -o /path/to/output_pickles -c "<continent>"

Arguments:
    -i, --data-input      (required) Path to the input folder containing .geojson files.
    -o, --data-output     (required) Path to the output folder to write .shp.pickle files.
    -c, --continent       (optional) Continent name used in feature IDs (default: "Africa").

Input Requirements:
    - Input files are expected to follow the GADM format, in which generally:
        - Each GeoJSON file must contain a "features" array with:
            - "properties": includes "COUNTRY", "NAME_1", and optionally "NAME_2"
            - "geometry": standard GeoJSON geometry

Output:
    - For each input file, a .shp.pickle file is generated.
    - Feature IDs take the form:
        Africa:Kenya                      # Level 0
        Africa:Kenya:Nairobi              # Level 1
        Africa:Kenya:Nairobi:Westlands    # Level 2
    - Output filenames are formatted as: <country>__l<level+1>__<shapefile_version>.shp.pickle
      Example: Kenya__l2__1.shp.pickle

Notes:
    - Input and output directories must exist; otherwise, a FileNotFoundError is raised.
"""

import argparse
import json
import os
import pickle
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)

def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--data-input', dest='input_folder', type=str, required=True,
                        help='Source directory containing data files. Expects a directory containing geojson files ('
                             'Required)')
    parser.add_argument('-o', '--data-output', dest='output_folder', type=str, required=True,
                        help='Directory to which converted .shp.pickle files are written (Required)')
    parser.add_argument('-c', '--continent', dest='continent', type=str,
                        default="Africa", help='Name of the continent in which the relevant country is located ('
                                               'Default: "Africa")')

    args = parser.parse_args()
    args.input_folder = Path(args.input_folder).absolute()
    args.output_folder = Path(args.output_folder).absolute()
    return args

def determine_admin_level(props):
    if "NAME_2" in props:
        return 2
    elif "NAME_1" in props:
        return 1
    else:
        return 0


def process_file(file_path, output_folder, continent):
    if not file_path.name.endswith((".geojson", ".json")):
        logging.info(f"Skipping unsupported file: {file_path.name}")
        return

    try:
        with file_path.open() as json_file:
            data = json.load(json_file)
    except (FileNotFoundError, PermissionError, json.JSONDecodeError) as e:
        logging.error(f"Error reading {file_path.name}: {e}")
        return

    if "features" not in data or not data["features"]:
        logging.warning(f"No 'features' found in {file_path.name}. Skipping.")
        return

    new_json = {}
    try:
        level = determine_admin_level(data["features"][0]["properties"])
    except Exception as e:
        logging.error(f"Could not determine admin level in {file_path.name}: {e}")
        return

    for feature in data["features"]:
        try:
            props = feature["properties"]
            geometry = feature["geometry"]
            feature_type = feature["type"]

            country = props["COUNTRY"]
            feature_id = f"{continent}:{country}"

            if level >= 1:
                admin1 = props["NAME_1"]
                feature_id += f":{admin1}"
            if level == 2:
                admin2 = props["NAME_2"]
                feature_id += f":{admin2}"

            new_json[feature_id] = {
                "type": feature_type,
                "id": feature_id,
                "properties": {
                    "country": country,
                    "TYPE": level,
                    "id": feature_id,
                    "name": feature_id.split(":")[-1]
                },
                "geometry": geometry
            }

        except KeyError as e:
            logging.warning(f"Missing expected key {e} in feature in {file_path.name}. Skipping feature.")
            continue
        except Exception as e:
            logging.warning(f"Error processing feature in {file_path.name}: {e}")
            continue

    output_filename = f"{country}__l{level+1}__1.shp.pickle"
    output_path = output_folder / output_filename
    try:
        with output_path.open("wb") as outfile:
            pickle.dump(new_json, outfile)
        logging.info(f"Wrote output to {output_filename}")
    except Exception as e:
        logging.error(f"Failed to write {output_filename}: {e}")

def main(args):
    if not args.input_folder.exists():
        raise FileNotFoundError(f"Input folder does not exist: {args.input_folder}")
    if not args.output_folder.exists():
        raise FileNotFoundError(f"Output folder does not exist: {args.output_folder}")

    for file in args.input_folder.iterdir():
        logging.info(f"Processing {file.name}")
        process_file(file, args.output_folder, args.continent)


if __name__ == '__main__':
    args = parse_args()
    main(args=args)
