import pandas as pd
import numpy as np
import json
import joblib
import sys
import datetime
import os
import glob
from tqdm import tqdm

sys.path.append('CC/')

from compound_cacher import CompoundCacher
from db_bulk_dg_gen import (
    load_smiles, load_molsig_rad1, load_molsig_rad2,
    load_model, parse_formula, get_dG0
)


def batch_predict_from_folder(input_folder='./tmp/input',
                              output_folder='./tmp/output',
                              pH=7.0, I=0.1):
    print("Loading resources...", flush=True)
    # db_smiles = load_smiles() # 如果没用到可以注释
    molsig_r1 = load_molsig_rad1()
    molsig_r2 = load_molsig_rad2()
    loaded_model = load_model()
    print("Resources loaded.", flush=True)

    # 确保输出目录存在
    os.makedirs(output_folder, exist_ok=True)

    input_files = glob.glob(os.path.join(input_folder, '*.json'))
    if not input_files:
        print(f"No input files found in {input_folder}")
        return

    for input_file in input_files:
        print(f'Processing {input_file}...')

        with open(input_file, 'r') as f:
            rxn_list = json.load(f)

        mu_ls = []
        std_ls = []
        kegg_id_ls = []

        # 使用 tqdm 显示进度
        for rxn_id, rxn_string in tqdm(rxn_list.items()):
            try:
                rxn_dict = parse_formula(rxn_string)
                mu, std, _, _ = get_dG0(
                    rxn_dict, rxn_id, pH, I,
                    loaded_model, molsig_r1, molsig_r2,
                    [], [], []
                )
                kegg_id_ls.append(rxn_id)
                mu_ls.append(mu)
                std_ls.append(std)
            except Exception as e:
                print(f'Error processing {rxn_id}: {e}')
                kegg_id_ls.append(rxn_id)
                mu_ls.append(np.NaN)
                std_ls.append(np.NaN)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        results = []
        for i in range(len(kegg_id_ls)):
            dg_value = mu_ls[i]
            std_value = std_ls[i]

            # 处理 numpy NaN 为 None，以便 JSON 序列化
            if pd.isna(dg_value):
                dg_value = None
            if pd.isna(std_value):
                std_value = None

            # [关键修复]：这里取消缩进，无论是否为空都添加到结果中
            results.append({
                'ID': kegg_id_ls[i],
                'dG': dg_value,
                'std': std_value
            })

        base_name = os.path.basename(input_file).replace('.json', '')
        output_file = os.path.join(output_folder, f'{base_name}_results_{timestamp}.json')

        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f'Results saved to {output_file}')


if __name__ == '__main__':
    batch_predict_from_folder()