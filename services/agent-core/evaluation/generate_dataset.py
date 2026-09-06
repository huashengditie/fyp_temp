# -*- coding: utf-8 -*-
import json
import random
import uuid
import os
import sys

# ==========================================================
# 1. Data Definitions 
# ==========================================================
REACTIONS = [
    "C01083 + C00001 <=> 2 C00031",
    "C00092 + C00001 <=> C00031 + C00009",
    "C00103 + C00001 <=> C00031 + C00009",
    "C15524 + C00001 <=> C02137 + C00010",
    "C00148 + C00026 + C00007 <=> C01157 + C00042 + C00011",
    "C00091 + C00149 <=> C00042 + C04348",
    "C00022 + C00001 <=> C00031 + C00011",
    "C00267 + C00001 <=> C00011 + C00042"
]

ENZYME_SUBSTRATE_PAIRS = [
    {"enzyme_seq": "MTKRVLVTGGAGFLGSHLCERLLSEGHEVICLDNFGSGRRKNIKEFEDHPSFKVNDRDVRISESLPSVDRIYHLASRASPADFTQFPVNIALANTQGTRRLLDQARACDARMVFASTSEVYGDPKVHPQPETYTGNVNIRGARGCYDESKRFGETLTVAYQRKYDVDARTVRIFNTYGPRMRPDDGRVVPTFVTQALRGDDLTIYGDGEQTRSFCYVDDLIEGLISLMRVDNPEHNVYNIGKENERTIKELAYEVLGLTDTESDIVYEPLPEDDPGQRRPDITRAKTELDWEPKISLREGLEDTITYFDN", "substrate_id": "C00149"},
    {"enzyme_seq": "MKRILVAGGAGFIGSHLCERLVNEGHYVVCLDNFFTGNKKKVEQLLNNPRFEIAKHDVIEPYFNEVDEIYNLACPASPIHYQVDPIKTIKTSVLGAMNMLGLAKKTNAKILQASTSEVYGEPEVHPQYEEYWGNVNPIGKRSCYNEGKRCAESLFINYHSQHQTKIKIIRIFNTYGPKMDINDGRVISNFVIQALKGKDITIYGDGKQTRSFQYVDDLVEGMIRMMNTDDSFTGPVNIGNPEEYTMLELVSFIIEMTQSKSKLIFLPLPEDDPKRRRPNIELAKKELNNWEPKIKLREGLIKTINYFEKII", "substrate_id": "C00022"},
    {"enzyme_seq": "MKYFSAAVIPGDGIGPEVMEVGMSLLQAIGDIHGGLSFEAESFPWNCRYYLQHGRMMPEDGLERLRPFDVILLGAIGAPGVPDHISVWELILPIRRSFQQYVNLRPIKLLRGLESPLRGKGHEHLDFVVVRENTEGEYSNMGGRLHVGTPYEMAMQNNVFTRYGTERIIRYAFELAQATGKTRLTAATKSNGINHSMPFWDEIVKEISLHYPNIQTSLIHIDALAAFFVSRPEAFDVVVASNLFGDILTDLGAAVVGGLGLAPSGNINPEKTYPSMFEPIHGSAPDIAGRGIANPIATIWSISMMLDHLGERELGRLVLDCIEEVLVEGKVRTPDIGGKATTQEMGKAILAQLYRRGG", "substrate_id": "C00497"},
    {"enzyme_seq": "MQTRILLVGGAGFIGSHLCE...", "substrate_id": "C00149"} # Added dummy to increase pairs
]

COMPOUNDS = ["Geranyl diphosphate", "Acyl-CoA", "Glucose", "ATP", "Pyruvate", "Malate", "Succinate", "Citrate", "Fructose", "Proline"]
UNIPROT_IDS = ["P00533", "P12345", "Q9WUA6", "P68871", "O00124", "Q12345", "P54321", "O98765"]

ME_PRODUCTS = ["succinate", "bhb", "fumarate", "citrate", "malate", "itaconate", "(R)-acetoin", "propan-2-ol"]
ME_MODELS = ["iML1515", "iJO1366"]

DG_TEMPLATES = [
    "Calculate dG for reaction: {reaction}",
    "What is the delta G of {reaction}?",
    "Predict thermodynamics for {reaction}",
    "Estimate the Gibbs free energy for {reaction}",
    "I need the dG value for: {reaction}",
    "Thermodynamic profile for {reaction}",
    "Spontaneity of {reaction}"
]

ENZ_TEMPLATES = [
    "Rank enzyme {seq} for substrate {sub}",
    "Compatibility score between {seq} and {sub}",
    "Is enzyme {seq} compatible with {sub}?",
    "Run EnzRank for protein {seq} on {sub}",
    "Enzyme interaction level: {seq} + {sub}",
    "Check affinity of {seq} to {sub}",
    "Will {seq} catalyze {sub}?",
    "Evaluate efficiency of {seq} with {sub}"
] # Increased to 8 templates to avoid loop stuck (4 pairs * 8 templates = 32 > 20)

ME_TEMPLATES = [
    "I want to produce {prod}. What is the best host and maximum theoretical yield?",
    "Find the alternative engineering designs for producing {prod} in {host} using D-glucose.",
    "What is the maximum yield of {prod} in {host}?",
    "List the target reactions for producing {prod}.",
    "Theoretical yield and engineering strategy for {prod}."
]

GREETING_CORPUS = [
            "Hello!",
            "Hi there.",
            "Good morning assistant.",
            "Yo.",
            "Hey bot!",
            "Is anyone there?",
            "Good evening.",
            "Hi, how are you?",
            "Greetings.",
            "Hello AI."
        ]

CAPABILITY_CORPUS = [
            "What can you do?",
            "List your available tools.",
            "How can you help me with biology?",
            "What are your capabilities?",
            "Show me your functions.",
            "What tasks can you perform?",
            "Tell me about your skills.",
            "How do you work?",
            "Give me a manual of your features.",
            "What kind of queries can I ask you?"
        ]
        
NEGATIVE_DG = [
            "Calculate the dG for pure water.",
            "What is the dG of compound C00031?",
            "Thermodynamics of reaction A + B",
            "Find the Gibbs free energy of C00001 + C00002 -> C00003",
            "What is the delta G of C01083 + C00001 <=> 2C00031?",
            "Calculate the thermodynamic value of ATP alone.",
            "Calculate dG for Glucose + ATP <=> G6P + ADP",
            "What is the standard free energy of sunlight?",
            "Compute the dG.",
            "Determine the Gibbs free energy for: [Insert Rxn]",
        ]


NEGATIVE_ENZ = [
            "Run EnzRank on protein MTKRVLL.", 
            "Rank the catalytic affinity between Glucose and ATP.", 
            "Evaluate protein folding for sequence MKTV...",
            "Score for Enzyme A",
            "Evaluate the interaction between two proteins MDH1 and LDHA.", 
            "Rank enzyme MKTV... for substrate 'Sugar'",
            "EnzRank sequence='ttaccagtctcacgatgttagattcgtat' substrate=C00001",
            "Check enzyme specificity.",
            "Is enzyme 'ACTGACTG' compatible with C00001?",
            "Can you rank the affinity of this enzyme without knowing the substrate?"
        ]


NEGATIVE_DB = [
            "Validate KEGG ID C031.", 
            "Search for compound glucose-8-phosphate.",
            "Fetch information about Uniprot ID 123456.", 
            "Is KEGG ID R000 valid?", 
            "Check KEGG ID 12345.", 
            "Look up the UniProt sequence",
            "Query the database for my novel synthesized compound.", 
            "Search database for [Insert Compound Here].", 
            "Validate UniProt ID: NULL.", 
            "Search KEGG for the reason why glycolysis produces ATP." 
        ]


NEGATIVE_ME = [
            "Find the maximum theoretical yield of succinate in Homo sapiens.", 
            "What is the best engineering strategy for producing malate in Arabidopsis thaliana?",
            "Calculate the theoretical yield of ethanol in Synechocystis sp. PCC 6803.",
            "Design a metabolic pathway for citrate production in Methanococcus maripaludis.",
            "What is the maximum theoretical yield of CRISPR Cas9 protein in Escherichia coli?", 
            "Find alternative engineering designs for producing monoclonal antibodies in Saccharomyces cerevisiae.",
            "Optimize Saccharomyces cerevisiae to maximize its cellular volume.", 
            "What is the optimal cultivation temperature for Bacillus subtilis?",
            "Calculate the yield of itaconate in [Insert Host Organism].", 
            "What is the theoretical maximum yield of fumarate in a generic bacterial cell?" 
        ]


NEGATIVE_GENERAL = [
            "What is the weather like today?",                       
            "Who is the current president of the United States?",  
            "Where can I find the best pizza recipe?",              
            "Can you translate 'hi' into Spanish?",                  
            "Write a short poem about cute cats.",
            "What is the result of 2 + 2?",   
            "How do I fix a flat tire on my car?",         
            "What is the current stock price of Apple?",    
            "What is the capital city of France?",       
            "Tell me a funny joke."                               
        ]
        
class DatasetGenerator:
    def __init__(self, total_expected=140):
        self.data = []
        self.seen_queries = set()
        self.total_expected = total_expected

    def _get_id(self, prefix):
        return f"{prefix}_{str(uuid.uuid4())[:8]}"

    def _print_progress(self):
        current = len(self.data)
        percent = (current / self.total_expected) * 100
        bar_length = 40
        filled_length = int(bar_length * current // self.total_expected)
        bar = '=' * filled_length + '-' * (bar_length - filled_length)
        sys.stdout.write(f'\rProgress: |{bar}| {percent:.1f}% ({current}/{self.total_expected} cases)')
        sys.stdout.flush()

    def _add_entry(self, entry):
        q = entry['query']
        if q in self.seen_queries: return False
        self.seen_queries.add(q)
        self.data.append(entry)
        self._print_progress()
        return True

    def gen_positive(self):
        # 1. dG (20)
        while len([x for x in self.data if x['category'] == 'dGPredictor']) < 20:
            rxn = random.choice(REACTIONS)
            t = random.choice(DG_TEMPLATES)
            self._add_entry({"id": self._get_id("dg"), "category": "dGPredictor", "query": t.format(reaction=rxn), "expected_tool": "dg_predictor_tool", "expected_args": {"reaction": rxn}})
        
        # 2. EnzRank (20)
        while len([x for x in self.data if x['category'] == 'EnzRank']) < 20:
            pair = random.choice(ENZYME_SUBSTRATE_PAIRS)
            t = random.choice(ENZ_TEMPLATES)
            q = t.format(seq=pair["enzyme_seq"], sub=pair["substrate_id"])
            self._add_entry({"id": self._get_id("enz"), "category": "EnzRank", "query": q, "expected_tool": "enzrank_tool", "expected_args": {"enzyme": pair["enzyme_seq"], "substrate": pair["substrate_id"]}})
        
        # 3. Database (20)
        db_templates = ["Search for {n}", "Find {n}", "Lookup {n}", "KEGG info on {n}", "Validate {n}"]
        while len([x for x in self.data if x['category'] == 'Database']) < 20:
            if random.random() > 0.5:
                n = random.choice(COMPOUNDS)
                t = random.choice(db_templates)
                self._add_entry({"id": self._get_id("db"), "category": "Database", "query": t.format(n=n), "expected_tool": "entity_search_tool", "expected_args": {"query": n, "category": "compound"}})
            else:
                uid = random.choice(UNIPROT_IDS)
                self._add_entry({"id": self._get_id("db"), "category": "Database", "query": f"Check UniProt {uid}", "expected_tool": "entity_validation_tool", "expected_args": {"entity_id": uid, "db_type": "UniProt"}})

        # 4. ME Search (5)
        while len([x for x in self.data if x['category'] == 'MESearch']) < 5:
            prod = random.choice(ME_PRODUCTS)
            host = random.choice(ME_MODELS)
            t = random.choice(ME_TEMPLATES)
            self._add_entry({
                "id": self._get_id("me"), 
                "category": "MESearch", 
                "query": t.format(prod=prod, host=host), 
                "expected_tool": "me_search_tool", 
                "expected_args": {"target_chemical": prod, "host": host}
            })

    def gen_others(self):
        for g in GREETING_CORPUS: self._add_entry({"id": self._get_id("greet"), "category": "Greeting", "query": g, "expected_tool": None, "expected_args": {}})
        for c in CAPABILITY_CORPUS: self._add_entry({"id": self._get_id("cap"), "category": "Capability", "query": c, "expected_tool": None, "expected_args": {}})
        for cat, src in [("Neg_dG", NEGATIVE_DG), ("Neg_Enz", NEGATIVE_ENZ), ("Neg_DB", NEGATIVE_DB), ("Neg_Gen", NEGATIVE_GENERAL), ("Neg_ME", NEGATIVE_ME)]:
            for q in src: self._add_entry({"id": self._get_id("neg"), "category": cat, "query": q, "expected_tool": None, "expected_args": {}})

    def gen_multi(self):
        for i in range(2):
            r1, r2 = REACTIONS[i], REACTIONS[i+1]
            self._add_entry({
                "id": self._get_id("multi_dg"), "category": "MultiTool_Same", "query": f"Calculate Gibbs for {r1} and {r2}", 
                "expected_tools": ["dg_predictor_tool", "dg_predictor_tool"], "expected_args_list": [{"reaction": r1}, {"reaction": r2}]
            })
        for i in range(3):
            p = ENZYME_SUBSTRATE_PAIRS[i % len(ENZYME_SUBSTRATE_PAIRS)]
            self._add_entry({
                "id": self._get_id("multi_enz"), "category": "MultiTool_Same", "query": f"Rank {p['enzyme_seq']} with C00149 and C00022",
                "expected_tools": ["enzrank_tool", "enzrank_tool"], "expected_args_list": [{"enzyme": p['enzyme_seq'], "substrate": "C00149"}, {"enzyme": p['enzyme_seq'], "substrate": "C00022"}]
            })
        for i in range(5):
            r, p = REACTIONS[i % len(REACTIONS)], ENZYME_SUBSTRATE_PAIRS[i % len(ENZYME_SUBSTRATE_PAIRS)]
            self._add_entry({
                "id": self._get_id("multi_mix"), "category": "MultiTool_Mixed", "query": f"dG for {r} and rank {p['enzyme_seq']} for {p['substrate_id']}",
                "expected_tools": ["dg_predictor_tool", "enzrank_tool"], "expected_args_list": [{"reaction": r}, {"enzyme": p['enzyme_seq'], "substrate": p['substrate_id']}]
            })

    def save(self):
        sys.stdout.write('\n')
        random.shuffle(self.data)
        out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_dataset_rich.json")
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        print(f"Total: {len(self.data)} cases saved to: {out_path}")

if __name__ == "__main__":
    gen = DatasetGenerator(total_expected=140)
    gen.gen_positive()
    gen.gen_others()
    gen.gen_multi()
    gen.save()