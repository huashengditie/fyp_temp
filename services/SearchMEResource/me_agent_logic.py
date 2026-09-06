import pandas as pd
import os
import glob
import re
import warnings

# Ignore openpyxl styling warnings
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

class MEResourceAgent:
    def __init__(self, dataset_path):
        self.dataset_path = dataset_path
        self.summarized_path = os.path.join(dataset_path, "SummarizedData")

        # Initialize attributes
        self.yield_df = pd.DataFrame()
        self.stoich = pd.DataFrame()
        self.met_info = pd.DataFrame()
        self.rxn_info = pd.DataFrame()
        self.met_name_dict = {}  # Map ID to Human-readable Name
        self.met_chebi_dict = {} # Map ID to ChEBI ID
        
        print("?? Initializing MEResource Agent Logic (V3 - EC Numbers & ChEBI Integration)...")
        self._load_databases()

    def _load_databases(self):
        # 1. Load TSV Databases
        tsv_files = {
            "stoich": 'ChemMap_Table - Stoichiometry.tsv',
            "met_info": 'ChemMap_Table - Metabolite_Info.tsv',
            "rxn_info": 'ChemMap_Table - Reaction_Info.tsv'
        }
        
        for attr, fname in tsv_files.items():
            fpath = os.path.join(self.summarized_path, fname)
            if os.path.exists(fpath):
                try:
                    df = pd.read_csv(fpath, sep='\t', dtype=str, encoding='utf-8')
                    df.columns = df.columns.str.strip()
                    setattr(self, attr, df)
                    print(f"? Loaded {fname} successfully.")
                except Exception as e:
                    print(f"? Error loading {fname}: {e}")
            else:
                print(f"?? WARNING: TSV file not found -> {fpath}")

        # Build translation dictionaries for IDs
        self._build_metabolite_dict()

        # 2. Load Yield Data (Scan Excels or Load Parquet Cache)
        cache_path = os.path.join(self.dataset_path, "ya_yield_data_cache.parquet")
        if os.path.exists(cache_path):
            try:
                self.yield_df = pd.read_parquet(cache_path)
            except Exception:
                self._scan_excels_to_cache(cache_path)
        else:
            self._scan_excels_to_cache(cache_path)

    def _build_metabolite_dict(self):
        """Builds dictionaries for Metabolite ID -> Name and Metabolite ID -> ChEBI ID."""
        if self.met_info.empty: return
        
        cols = self.met_info.columns
        id_col = cols[0]
        name_col = cols[1]
        chebi_col = None
        
        # Flexible matching for Name and ChEBI columns
        for c in cols:
            if 'name' in c.lower() or 'synonym' in c.lower():
                name_col = c
            if 'chebi' in c.lower():
                chebi_col = c

        for _, row in self.met_info.iterrows():
            m_id = str(row[id_col]).strip()
            # Map Name
            m_name = str(row[name_col]).strip()
            if m_name.lower() not in ['nan', 'none', '']:
                self.met_name_dict[m_id] = m_name
            # Map ChEBI
            if chebi_col:
                c_id = str(row[chebi_col]).strip()
                if c_id.lower() not in ['nan', 'none', '']:
                    self.met_chebi_dict[m_id] = c_id

    def _get_met_name(self, m_id):
        return self.met_name_dict.get(str(m_id).strip(), str(m_id))

    def _get_met_chebi(self, m_id):
        return self.met_chebi_dict.get(str(m_id).strip(), "Unknown")

    def _scan_excels_to_cache(self, cache_path):
        excel_files = glob.glob(os.path.join(self.dataset_path, "*.xlsx"))
        all_dfs = []
        for file in excel_files:
            filename = os.path.basename(file)
            if filename.startswith('~$'): continue
            match = re.search(r'MOESM(\d+)_ESM', filename)
            if not match: continue
            file_num = int(match.group(1))
            
            category = 'Base_YA' if 2 <= file_num <= 6 else \
                       'Hetero_YA' if 32 <= file_num <= 36 else \
                       'Cofactor_YA' if 37 <= file_num <= 39 else None
            if not category: continue

            try:
                df = pd.read_excel(file)
                df.columns = df.columns.astype(str).str.strip()
                df = df.rename(columns={
                    'Target reaction': 'Target reactions',
                    'Improved YT (mol/mol)': 'molar yield (mol/mol)',
                    'Target ID': 'Target ID'
                })
                df['Source_File'] = filename
                all_dfs.append(df)
            except Exception: continue

        if all_dfs:
            self.yield_df = pd.concat(all_dfs, ignore_index=True)
            self.yield_df['molar yield (mol/mol)'] = pd.to_numeric(self.yield_df['molar yield (mol/mol)'], errors='coerce')
            self.yield_df.to_parquet(cache_path, index=False)

    def query_design(self, product_name, host_name=None, carbon=None):
        if self.yield_df.empty: return {"status": "error", "message": "Yield database is empty"}

        df = self.yield_df.copy()
        mask = (df['Target ID'].astype(str).str.lower() == product_name.lower()) | \
               (df['Target chemical'].astype(str).str.contains(product_name, case=False, na=False))
        
        if host_name:
            mask &= (df['Template model'].astype(str).str.contains(host_name, case=False, na=False) |
                     df['Target model'].astype(str).str.contains(host_name, case=False, na=False))
        
        if carbon and 'Carbon source' in df.columns:
            mask &= (df['Carbon source'].astype(str).str.contains(carbon, case=False, na=False))
        
        results = df[mask].dropna(subset=['molar yield (mol/mol)'])
        if results.empty: return {"status": "empty", "message": "No design found"}

        null_list = ['None', 'nan', '', '\u65e0']
        results['has_rxn'] = results['Target reactions'].apply(lambda x: 0 if str(x).strip() in null_list else 1)
        results = results.sort_values(by=['has_rxn', 'molar yield (mol/mol)'], ascending=[False, False])

        top_5_designs = []
        seen_rxns = set()
        for _, row in results.iterrows():
            rxn_str = str(row.get('Target reactions', 'None')).strip()
            if rxn_str in seen_rxns: continue
            seen_rxns.add(rxn_str)
            
            rxn_details = self._build_reaction_list(rxn_str)
            top_5_designs.append({
                "product": row.get('Target chemical', product_name),
                "yield": float(row['molar yield (mol/mol)']),
                "host": row.get('Template model', 'N/A'),
                "carbon": row.get('Carbon source', 'N/A'),
                "reactions_list": [r.strip() for r in rxn_str.split(';') if r not in null_list],
                "detailed_pathway": rxn_details,
                "net_equation": self._calculate_net_equation(rxn_details),
                "source": row.get('Source_File', 'N/A')
            })
            if len(top_5_designs) >= 5: break

        return {"status": "success", "top_designs": top_5_designs}

    def _build_reaction_list(self, rxn_ids_str):
        null_list = ['None', 'nan', '', '\u65e0']
        if not rxn_ids_str or str(rxn_ids_str).strip() in null_list: return []
            
        rxn_ids = [r.strip() for r in str(rxn_ids_str).split(';')]
        full_results = []
        
        col1, col2 = self.stoich.columns[0], self.stoich.columns[1]
        idx_list = self.stoich.index[self.stoich[col1] == 'RXN_ID'].tolist()

        for original_id in rxn_ids:
            clean_rxn_id = str(original_id).split('.')[0].strip()
            rhea_id, enz_name, ec_num = clean_rxn_id, "Unknown", "Unknown"
            
            # --- EXTRACT EC NUMBER FROM RXN_INFO ---
            if not self.rxn_info.empty:
                match = self.rxn_info[self.rxn_info.apply(lambda row: clean_rxn_id in str(row.values), axis=1)]
                if not match.empty:
                    rhea_id = str(match.iloc[0, 0]).strip()
                    enz_name = str(match.iloc[0, 1]).strip()
                    # EC is typically in the 5th column (index 4)
                    if len(match.columns) > 4:
                        raw_ec = str(match.iloc[0, 4]).strip()
                        ec_num = raw_ec if raw_ec.lower() not in ['nan', '', 'none'] else "Unknown"

            rxn_data = {"id": clean_rxn_id, "rhea": rhea_id, "name": enz_name, "ec": ec_num, "equation": "", "mets": []}
            
            for idx in idx_list:
                if str(self.stoich.iloc[idx][col2]).strip().lower() == rhea_id.lower():
                    m_ids = self.stoich.iloc[idx+1, 1:].dropna().tolist()
                    coeffs = self.stoich.iloc[idx+2, 1:].dropna().tolist()
                    reactants, products = [], []
                    for m, c in zip(m_ids, coeffs):
                        c_val = float(c)
                        rxn_data["mets"].append({"id": m, "coeff": c_val, "name": self._get_met_name(m), "chebi": self._get_met_chebi(m)})
                        prefix = f"{abs(c_val)} " if abs(c_val) != 1.0 else ""
                        if c_val < 0: reactants.append(f"{prefix}{self._get_met_name(m)}")
                        else: products.append(f"{prefix}{self._get_met_name(m)}")
                    rxn_data["equation"] = f"{' + '.join(reactants)} -> {' + '.join(products)}"
                    break
            full_results.append(rxn_data)
        return full_results

    def _calculate_net_equation(self, rxn_details):
        if not rxn_details: return "N/A"
        reactants, products = {}, {}
        for r in rxn_details:
            for m in r["mets"]:
                mid, c = m["id"], m["coeff"]
                if c < 0: reactants[mid] = reactants.get(mid, 0) + abs(c)
                else: products[mid] = products.get(mid, 0) + c
        
        for mid in list(reactants.keys()):
            if mid in products:
                net = reactants[mid] - products[mid]
                if net > 0: reactants[mid], _ = net, products.pop(mid)
                elif net < 0: products[mid], _ = -net, reactants.pop(mid)
                else: reactants.pop(mid), products.pop(mid)

        r_str = " + ".join([f"{v} {self._get_met_name(k)}" if v != 1 else self._get_met_name(k) for k, v in reactants.items()])
        p_str = " + ".join([f"{v} {self._get_met_name(k)}" if v != 1 else self._get_met_name(k) for k, v in products.items()])
        return f"{r_str} -> {p_str}" if r_str or p_str else "No net equation"