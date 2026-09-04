import pandas as pd
import numpy as np
import json
import sys
import os
import argparse
from tqdm import tqdm

sys.path.append('CC/')

from compound_cacher import CompoundCacher
from db_bulk_dg_gen import (
    load_smiles, load_molsig_rad1, load_molsig_rad2,
    load_model, parse_formula, get_dG0
)


def predict_single_file(input_file, output_file, pH=7.0, I=0.1):
    """
    Take the input_file, perform calculations, and write the results to output_file.
    """
    print("Loading resources...", flush=True)

    # db_smiles = load_smiles()
    molsig_r1 = load_molsig_rad1()
    molsig_r2 = load_molsig_rad2()
    loaded_model = load_model()
    print("Resources loaded.", flush=True)

    print(f'Processing file: {input_file}...')

    try:
        with open(input_file, 'r') as f:
            rxn_list = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file not found at {input_file}")
        sys.exit(1)

    results = []

    for rxn_id, rxn_string in tqdm(rxn_list.items()):
        dg_value = None
        std_value = None

        try:
            rxn_dict = parse_formula(rxn_string)

            mu, std, _, _ = get_dG0(
                rxn_dict, rxn_id, pH, I,
                loaded_model, molsig_r1, molsig_r2,
                [], [], []
            )

            dg_value = mu
            std_value = std

        except Exception as e:
            print(f'Error processing {rxn_id}: {e}')
            dg_value = None
            std_value = None

        if pd.isna(dg_value):
            dg_value = None
        if pd.isna(std_value):
            std_value = None

        results.append({
            'ID': rxn_id,
            'Equation': rxn_string,
            'dG': dg_value,
            'std': std_value,
            'units': 'kJ/mol'
        })

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f'Results successfully saved to {output_file}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run dG prediction on a specific JSON file.')
    parser.add_argument('--input_file', type=str, required=True, help='Path to input JSON file')
    parser.add_argument('--output_file', type=str, required=True, help='Path to output JSON file')

    args = parser.parse_args()

    predict_single_file(args.input_file, args.output_file)