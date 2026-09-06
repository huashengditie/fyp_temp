import os

class Config:
    DG_PREDICTOR_URL = os.getenv("DG_PREDICTOR_URL", "http://127.0.0.1:8002/predict")
    ENZRANK_URL = os.getenv("ENZRANK_URL", "http://127.0.0.1:8003/rank")
    MERESOURCE_URL = os.getenv("MERESOURCE_URL", "http://127.0.0.1:8004")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    EQUILIBRATOR_URL = os.getenv("EQUILIBRATOR_URL", "http://127.0.0.1:8005/calculate") 
    #MODEL_NAME = "llama3.1"
    MODEL_NAME = "qwen2.5:7b"
    #MODEL_NAME = "mistral-nemo"

    KEGG_API_URL = "https://rest.kegg.jp"
    RHEA_API_URL = "https://www.rhea-db.org/rhea"
    UNIPROT_API_URL = "https://rest.uniprot.org/uniprotkb"