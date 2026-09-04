import streamlit as st
import pandas as pd
import numpy as np
import re
# from PIL import Image
import json
import joblib
import sys

# sys.path.append('CC/')

from compound import Compound
from compound_cacher import CompoundCacher
from rdkit.Chem import rdChemReactions as Reactions
from rdkit.Chem import Draw
from rdkit import Chem
from tqdm import tqdm


def load_smiles():
    db = pd.read_csv('data/cache_compounds_20160818.csv',
                     index_col='compound_id')
    db_smiles = db['smiles_pH7'].to_dict()
    return db_smiles


def load_molsig_rad1():
    molecular_signature_r1 = json.load(open('data/decompose_vector_ac.json'))
    return molecular_signature_r1


def load_molsig_rad2():
    molecular_signature_r2 = json.load(
        open('data/decompose_vector_ac_r2_py3_indent_modified_manual.json'))
    return molecular_signature_r2


def load_model():

    filename = 'model/M12_model_BR.pkl'
    loaded_model = joblib.load(open(filename, 'rb'))
    return loaded_model


def load_compound_cache():
    ccache = CompoundCacher()
    return ccache


def count_substructures(radius, molecule):
    m = molecule
    smi_count = dict()
    atomList = [atom for atom in m.GetAtoms()]

    for i in range(len(atomList)):
        env = Chem.FindAtomEnvironmentOfRadiusN(m, radius, i)
        atoms = set()
        for bidx in env:
            atoms.add(m.GetBondWithIdx(bidx).GetBeginAtomIdx())
            atoms.add(m.GetBondWithIdx(bidx).GetEndAtomIdx())

        if len(atoms) == 0:
            atoms = {i}

        smi = Chem.MolFragmentToSmiles(m, atomsToUse=list(atoms),
                                       bondsToUse=env, canonical=True)

        if smi in smi_count:
            smi_count[smi] = smi_count[smi] + 1
        else:
            smi_count[smi] = 1
    return smi_count


def decompse_novel_mets_rad1(novel_smiles, radius=1):
    decompose_vector = dict()
    for cid, smiles_pH7 in novel_smiles.items():
        mol = Chem.MolFromSmiles(smiles_pH7)
        mol = Chem.RemoveHs(mol)
        smi_count = count_substructures(radius, mol)
        decompose_vector[cid] = smi_count
    return decompose_vector


def decompse_novel_mets_rad2(novel_smiles, radius=2):
    decompose_vector = dict()
    for cid, smiles_pH7 in novel_smiles.items():
        mol = Chem.MolFromSmiles(smiles_pH7)
        mol = Chem.RemoveHs(mol)
        smi_count = count_substructures(radius, mol)
        decompose_vector[cid] = smi_count
    return decompose_vector


def parse_reaction_formula_side(s):
    if s.strip() == "null":
        return {}
    compound_bag = {}
    for member in re.split('\s+\+\s+', s):
        tokens = member.split(None, 1)
        if len(tokens) == 0:
            continue
        if len(tokens) == 1:
            amount = 1
            key = member
        else:
            amount = float(tokens[0])
            key = tokens[1]
        compound_bag[key] = compound_bag.get(key, 0) + amount
    return compound_bag


def parse_formula(formula, arrow='<=>', rid=None):
    tokens = formula.split(arrow)
    if len(tokens) < 2:
        print(('Reaction does not contain the arrow sign (%s): %s'
               % (arrow, formula)))
    if len(tokens) > 2:
        print(('Reaction contains more than one arrow sign (%s): %s'
               % (arrow, formula)))

    left = tokens[0].strip()
    right = tokens[1].strip()

    sparse_reaction = {}
    for cid, count in parse_reaction_formula_side(left).items():
        sparse_reaction[cid] = sparse_reaction.get(cid, 0) - count

    for cid, count in parse_reaction_formula_side(right).items():
        sparse_reaction[cid] = sparse_reaction.get(cid, 0) + count

    return sparse_reaction


def get_rule(rxn_dict, molsig1, molsig2, novel_decomposed1, novel_decomposed2):
    """
    Optimized version of get_rule to avoid OOM (Out Of Memory).
    """
    # 1. Update novel compounds if they exist
    if novel_decomposed1 is not None:
        molsig1.update(novel_decomposed1)
    if novel_decomposed2 is not None:
        molsig2.update(novel_decomposed2)

    # 2. Load feature names (Group Names)
    try:
        moieties_r1 = open('data/group_names_r1.txt').read().splitlines()
        moieties_r2 = open('data/group_names_r2_py3_modified_manual.txt').read().splitlines()
    except FileNotFoundError:
        try:
            moieties_r1 = open('CC/data/group_names_r1.txt').read().splitlines()
            moieties_r2 = open('CC/data/group_names_r2_py3_modified_manual.txt').read().splitlines()
        except FileNotFoundError:
            moieties_r1 = open('../data/group_names_r1.txt').read().splitlines()
            moieties_r2 = open('../data/group_names_r2_py3_modified_manual.txt').read().splitlines()

    # 3. Create mapping for fast lookup (Feature Name -> Index)
    feat_map_r1 = {name: i for i, name in enumerate(moieties_r1)}
    feat_map_r2 = {name: i for i, name in enumerate(moieties_r2)}

    # 4. Initialize zero vectors (1 row, N columns)
    vec_r1 = np.zeros((1, len(moieties_r1)))
    vec_r2 = np.zeros((1, len(moieties_r2)))

    # 5. Calculate Reaction Vector R1
    for met, stoic in rxn_dict.items():
        if met in ["C00080", "C00282"]: continue  # Skip H2O / H+

        comp_sig = molsig1.get(met, {})
        for grp, count in comp_sig.items():
            if grp in feat_map_r1:
                idx = feat_map_r1[grp]
                vec_r1[0, idx] += count * stoic

    # 6. Calculate Reaction Vector R2
    for met, stoic in rxn_dict.items():
        if met in ["C00080", "C00282"]: continue

        comp_sig = molsig2.get(met, {})
        for grp, count in comp_sig.items():
            if grp in feat_map_r2:
                idx = feat_map_r2[grp]
                vec_r2[0, idx] += count * stoic

    # 7. Add Padding Zeros (Legacy model requirement: 44 zeros)
    zeros_pad = np.zeros((1, 44))

    X1 = np.concatenate((vec_r1, zeros_pad), axis=1)
    X2 = np.concatenate((vec_r2, zeros_pad), axis=1)

    # 8. Combine final feature vector
    rule_comb = np.concatenate((X1, X2), axis=1)

    # rule_df1 和 rule_df2 在预测逻辑中通常不被使用，为了省内存返回 None
    return rule_comb, None, None


def get_ddG0(rxn_dict, pH, I, novel_mets):
    ccache = CompoundCacher()
    T = 298.15
    ddG0_forward = 0
    for compound_id, coeff in rxn_dict.items():
        if novel_mets != None and compound_id in novel_mets:
            comp = novel_mets[compound_id]
        else:
            comp = ccache.get_compound(compound_id)
        ddG0_forward += coeff * comp.transform_pH7(pH, I, T)
    return ddG0_forward


def get_dG0(rxn_dict, rid, pH, I, loaded_model, molsig_r1, molsig_r2, novel_decomposed_r1, novel_decomposed_r2,
            novel_mets):
    rule_comb, _, _ = get_rule(
        rxn_dict, molsig_r1, molsig_r2, novel_decomposed_r1, novel_decomposed_r2)

    X = rule_comb

    ymean, ystd = loaded_model.predict(X, return_std=True)

    # 95% Confidence Interval approximation
    conf_int = (1.96 * ystd[0]) / np.sqrt(4001)

    return ymean[0] + get_ddG0(rxn_dict, pH, I, novel_mets), conf_int, None, None


def parse_novel_molecule(add_info):
    result = {}
    for cid, InChI in add_info.items():
        c = Compound.from_inchi('Test', cid, InChI)
        result[cid] = c
    return result


def parse_novel_smiles(result):
    novel_smiles = {}
    for cid, c in result.items():
        smiles = c.smiles_pH7
        novel_smiles[cid] = smiles
    return novel_smiles