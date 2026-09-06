import pandas as pd
import numpy as np
import os
import sys

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import tensorflow as tf
from keras.utils import pad_sequences
from rdkit import Chem
from rdkit.Chem import AllChem

SEQ_RDIC = ['A', 'I', 'L', 'V', 'F', 'W', 'Y', 'N', 'C', 'Q', 'M',
            'S', 'T', 'D', 'E', 'R', 'H', 'K', 'G', 'P', 'O', 'U', 'X', 'B', 'Z']
SEQ_DIC = {w: i + 1 for i, w in enumerate(SEQ_RDIC)}


class EnzRankService:
    def __init__(self, model_path='./CNN_model_final/Final_model.model', csv_path='CNN_data_kegg/kegg_compound.csv'):
        """
        Initialize service: load models and data, only runs once when service starts.
        """
        print("EnzRank: Initializing service...", flush=True)
        self.model = self._load_model(model_path)
        self.kegg_df = self._load_data(csv_path)
        print("EnzRank: Service ready.", flush=True)

    def _load_model(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model not found at: {path}")
        print("EnzRank: Loading TensorFlow model...", flush=True)
        return tf.keras.models.load_model(path, compile=False)

    def _load_data(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Data not found at: {path}")
        print("EnzRank: Loading KEGG data...", flush=True)
        df = pd.read_csv(path, index_col='Compound_ID')
        return df.reset_index()

    def _encode_seq(self, seq):
        if pd.isnull(seq) or seq == "":
            return [0]
        
        encoded = []
        for aa in seq:
            if aa not in SEQ_DIC:
                raise ValueError(f"Invalid character '{aa}' detected in protein sequence. Only standard amino acids {SEQ_RDIC} are allowed.")
            encoded.append(SEQ_DIC[aa])
        return encoded

    def _prot_feature_gen(self, prot_input_str, prot_len=2500):
        """
        Process protein sequence input, supporting automatic ID completion
        """
        if ':' in prot_input_str:
            parts = prot_input_str.split(':')
            prot_id = parts[0]
            prot_seq = parts[1] if len(parts) > 1 else ""
        else:
            prot_id = "AutoID"
            prot_seq = prot_input_str

        prot_seq = prot_seq.replace(" ", "").upper()

        if not prot_seq:
            raise ValueError(f"Empty protein sequence extracted from input: {prot_input_str}")

        encoded = self._encode_seq(prot_seq)
        
        prot_feature = pad_sequences([encoded], prot_len)
        return prot_feature, prot_id

    def _mol_feature_gen(self, mol_str, kegg_id_flag):
        if kegg_id_flag == 1:
            kegg_id = mol_str
            matches = self.kegg_df.index[self.kegg_df.Compound_ID == kegg_id]
            if len(matches) == 0:
                raise ValueError(f"KEGG ID {kegg_id} not found in database.")

            kegg_id_loc = matches[0]
            info = self.kegg_df.loc[kegg_id_loc]
            info_df = info.to_frame().T.set_index('Compound_ID')
            return info_df, kegg_id
        else:
            parts = mol_str.split(':')
            mol_id = parts[0]
            mol_smiles = parts[1] if len(parts) > 1 else ""

            mol = Chem.MolFromSmiles(mol_smiles)
            if mol is None:
                raise ValueError(f"Invalid SMILES string: {mol_smiles}")

            fp1 = AllChem.GetMorganFingerprintAsBitVect(mol, useChirality=True, radius=2, nBits=2048)
            fp_list = list(np.array(fp1).astype(float))
            mol_fp = '\t'.join(map(str, fp_list))

            mol_info_df = pd.DataFrame([{
                'Compound_ID': mol_id,
                'Smiles': mol_smiles,
                'morgan_fp_r2': mol_fp
            }]).set_index('Compound_ID')

            return mol_info_df, mol_id

    def _compound_feature_gen(self, comp_id, prot_id, comp_df, comp_vec='morgan_fp_r2'):
        act_df = pd.DataFrame({'Protein_ID': prot_id, 'Compound_ID': comp_id}, index=[0])
        # Merge
        merged = pd.merge(act_df, comp_df, left_on='Compound_ID', right_index=True)
        # Parse features
        comp_feature = np.stack(merged[comp_vec].map(lambda fp: fp.split("\t")))
        return comp_feature.astype('float')

    def predict_single(self, item):
        try:
            enzyme_str = item.get('enzyme', '')
            substrate_str = item.get('substrate', '')
            use_smiles = item.get('use_smiles', False)
            smiles_info = item.get('smiles_info', '')

            if not enzyme_str:
                raise ValueError("Missing 'enzyme' field")
            if not substrate_str:
                raise ValueError("Missing 'substrate' field")

            prot_feature, prot_id = self._prot_feature_gen(enzyme_str)

            if use_smiles and smiles_info:
                comp_df, comp_id = self._mol_feature_gen(smiles_info, 0)
            else:
                comp_df, comp_id = self._mol_feature_gen(substrate_str, 1)

            comp_feature = self._compound_feature_gen(comp_id, prot_id, comp_df)

            y = self.model.predict([comp_feature, prot_feature], verbose=0)
            score = float(y[0][0])

            return {
                'protein_id': prot_id,
                'compound_id': comp_id,
                'enzrank_score': score,
                'status': 'success',
                'error': None
            }

        except Exception as e:
            return {
                'protein_id': None,
                'compound_id': None,
                'enzrank_score': None,
                'status': 'error',
                'error': str(e)
            }

    def predict_batch(self, data_list):
        """
        Main Entrance: Process Batch Data List
        """
        results = []
        for idx, item in enumerate(data_list):
            res = self.predict_single(item)
            res['input_index'] = idx
            results.append(res)
        return results


if __name__ == "__main__":
    print("This module is designed to be imported by server.py.")
    print("To test manually, instantiate EnzRankService and call predict_batch.")