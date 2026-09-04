# Pathway Agent

Pathway Agent is an intelligent assistant designed for strain and pathway engineering in sythetic biology. Built on LLM reasoning via LangGraph, it integrates specialized microservices to automate pathway design, enzyme ranking, and feasibility analysis.

## Architecture & Ports

The system uses a microservices architecture. All services are isolated via **Apptainer (Singularity)** containers:

| Service              | Port | Description                                                                      | Source                                                                                                                                                                                                                               |
| -------------------- | ---- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **dGPredictor**      | 8002 | ML-based reaction thermodynamics (ΔG) prediction | [maranasgroup/dGPredictor](https://www.google.com/url?sa=E&q=https%3A%2F%2Fgithub.com%2Fmaranasgroup%2FdGPredictor)                                                                                                                  |
| **EnzRank**          | 8003 | Enzyme-substrate compatibility scoring (GPU supported)                           | [maranasgroup/EnzRank](https://www.google.com/url?sa=E&q=https%3A%2F%2Fgithub.com%2Fmaranasgroup%2FEnzRank)                                                                                                                          |
| **SearchMEResource** | 8004 | Metabolic engineering database & yield search                                    | [KAIST/MEResource](https://www.google.com/url?sa=E&q=https%3A%2F%2Fgithub.com%2Fkaistsystemsbiology%2FMEResource) & [Nature Article](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.nature.com%2Farticles%2Fs41467-025-58227-1) |
| **eQuilibrator**     | 8005 | Standard biochemical thermodynamics API                                          | [eQuilibrator API](https://www.google.com/url?sa=E&q=https%3A%2F%2Fequilibrator.readthedocs.io%2F)                                                                                                                                   |
| **Agent Core**       | 8081 | Orchestration Hub (LangGraph/FastAPI)                                            |                                                                                                                                                                                                                                      |
| **Frontend**         | 8501 | Web Interface (Streamlit)                                                        |                                                                                                                                                                                                                                      |
## Project Directory Structure  
```
pathway_agent/
├── deploy_dev.sh        
├── data/
│   └── agent_memory/    
├── logs/                
├── images/              
└── services/            
    ├── SearchMEResource/
    ├── dGPredictor/     
    ├── equilibrator/    
    ├── EnzRank/        
    ├── frontend/        
    └── agent-core/      
        ├── main.py      
        └── app/
            ├── config.py
            ├── agents/  
            └── tools/   
```
---
## Prerequisites

Ensure the following environments are installed on your Linux machine:

1. **Operating System**: Linux (Ubuntu 20.04/22.04 recommended).
    
2. **Apptainer**: Required to run .sif containers. [Installing Apptainer — Apptainer Admin Guide main documentation](https://apptainer.org/docs/admin/main/installation.html)
3. **Ollama**: Local LLM inference engine.
    - Install: curl -fsSL https://ollama.com/install.sh | sh
    - Ensure it is running at http://127.0.0.1:11434.

##  Quick Deployment

### 1. Download the Full Release

Do not use git clone alone, as large model weights and local databases are excluded from Git. Download the full asset package:
1. Go to the **Releases** page of this repository.
2. Download pathway_agent_full_vX.X.tar.gz.
3. Extract and enter the directory:
```
tar -xzvf pathway_agent_full_v1.1.tar.gz
cd pathway_agent
```
Note: The deployment script defaults to $HOME/pathway_agent. If you extracted it elsewhere, you must edit line 4 of deploy_dev.sh:
```
# Edit deploy_dev.sh
BASE_DIR=/your/actual/absolute/path/pathway_agent
```

### 2. Prepare LLM

The system uses qwen2.5:7b by default. Pull the model via Ollama:
```
ollama pull qwen2.5:7b
```
Note: To change the model, please modify the MODEL_NAME variable in services/agent-core/app/config.py and pull the corresponding model

### 3. Build Apptainer Images
Build the .sif images in the images/ directory. This step is required before the first run:
```
cd services/SearchMEResource && apptainer build ../../images/search_me.sif search_me.def && cd ../..

cd services/eQuilibrator && apptainer build ../../images/equilibrator.sif equilibrator.def && cd ../..

cd services/agent-core && apptainer build ../../images/agent.sif agent.def && cd ../..

cd services/dGPredictor && apptainer build ../../images/dg.sif dg.def && cd ../.. 

cd services/EnzRank && apptainer build ../../images/enz.sif enzrank.def && cd ../.. 

cd services/frontend && apptainer build ../../images/frontend.sif frontend.def && cd ../..
```

### 4. Start the Services
Grant execution permissions and run the deployment script:
```
chmod +x deploy_dev.sh
./deploy_dev.sh
```

**nitialization**:  
The first startup involves heavy data processing and model loading. Please wait 2–5 minutes before use.
1. **Cleanup**: The script automatically kills old uvicorn/streamlit processes and container instances.
2. **SearchMEResource (8004)**:
    - Slow Cold Start: On first run, it compiles dozens of Excel files into a .parquet cache. Takes 1–3 minutes.
3. **eQuilibrator (8005)**:
    -  Loads a 1.5GB thermodynamic database into memory. Takes 1–2 minutes every time.
4. **dGPredictor & EnzRank (8002, 8003)**:
    - Loads CNN model weights into memory/GPU. Takes ~20 seconds.
5. **Agent Core (8081)**:
    - The hub starts last. Check tail -f logs/search_me.log to confirm status.

## Usage

./deploy_dev.sh
Once the terminal displays Deployment completed

ssh -L 8501:127.0.0.1:8501 -L 8081:127.0.0.1:8081 <your_username>@<your_server_ip>
Acess Web UI: [http://localhost:8501](https://www.google.com/url?sa=E&q=http%3A%2F%2Flocalhost%3A8501)


##  Stop Services

To shut down the entire system and all background containers:
```
# Kill web processes
pkill -f uvicorn
pkill -f streamlit

# Stop all Apptainer instances
apptainer instance stop --all
```

##  Troubleshooting

1. **Frontend displays "Error: Connection Error" or "Tool Execution Failed"**
   - **Check Service Logs**: Inspect the specific backend service logs: `tail -f logs/<service_name>.log`.
   - **Verify Ollama**: Ensure the Ollama server is running locally by executing: `curl http://127.0.0.1:11434`.

1. **Inspect the Agent's reasoning process**
   - **In the UI**: Every response in the chat interface contains an expandable section labeled "View Tool Execution Logs (Internal)". Use this to verify tool calls, input parameters, and raw outputs.
   - **In the Backend**: For detailed execution flow and LangGraph states, monitor the Agent Core logs: `tail -f logs/agent.log`.

1. **Port Conflicts**
   - If the default ports (8002-8005, 8081, or 8501) are occupied by other programs, you must synchronize the changes in two files:
     - `deploy_dev.sh`: Update the port numbers in the startup commands.
     - `services/agent-core/app/config.py`: Update the service URLs to match the new ports.

---
##  Sample Queries and Input Outputs

| Category                     | Query Sample                                                                              | Function                                                                                          | Input                                               | Output                                                  |
| ---------------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | --------------------------------------------------- | ------------------------------------------------------- |
| **dGPredictor/eQuilibrator** | "Calculate the Gibbs free energy for the reaction: C01083 + C00001 <=> 2 C00031"          | Predicts the standard Gibbs free energy change for a biochemical reaction.                        | reaction: KEGG reaction string                      | Predicted ΔGvalue (kJ/mol) and uncertainty.             |
| **EnzRank**                  | "Rank the affinity between enzyme sequence MTKRV...[Full Seq]...FDN and substrate C00149" | Evaluates the catalytic compatibility or binding affinity between a protein and a substrate.(0-1) | enzyme: Amino acid sequence; substrate: Compound ID | Interaction score or affinity ranking.                  |
| **Database**                 | "Search for information on the compound Geranyl diphosphate"                              | Retrieves detailed metadata for biological entities from databases like KEGG or UniProt.          | query: Compound name; category: Entity type         | Compound details (formula, mass, structure).            |
| **MESearch**                 | "What is the maximum theoretical yield of succinate in host model iML1515?"               | Analyzes metabolic models to determine production limits and engineering strategies.              | target_chemical: Product name; host: Model ID       | Theoretical yield value and suggested reaction targets. |


# Evaluation Steps

```
# Gen test set and run agent
apptainer exec images/agent.sif bash services/agent-core/evaluation/run_tests.sh

# Judge llm scoring
apptainer exec images/agent.sif bash services/agent-core/evaluation/run_scoring.sh
```
 
---

# FYP Presentation Slides & Reports

All meeting slides and progress reports, thesis (pdf & latex) are uploaded. See shared document on Teams.
 [Teams and Channels | FYP-AY25 | Microsoft Teams](https://teams.microsoft.com/v2/)
To find prompts for Agent Core and judge LLM, go to Teams FYP-AY25/Shen Xintong/prompts.txt


# ⚡ One-Click Start

If you are on a Linux machine, follow these steps to deploy the entire system automatically.

**Upload the package to your server, then run**

```
tar -xzvf pathway_agent_full_v1.2.tar.gz
cd pathway_agent
```

**Run the Setup Script**
The setup_user.sh script will automatically check for Apptainer and Ollama, install them locally if they are missing, pull the LLM, build all microservice images, and launch the system.
```
chmod +x setup_user.sh deploy_dev.sh

bash setup_user.sh
```

**Completion**
Once the script finishes, you will see the following message:
```
=================================================================
SETUP COMPLETE!
If you are using a local Ollama, it is running in the background.
Access UI: http://localhost:8501
=================================================================
```

**Accessing the UI**

**Local Machine **: Open your browser and go to: http://localhost:8501

**Remote Server** (SSH Tunneling)：
If the system is running on a remote server, run this on your local computer's terminal:
```
ssh -L 8501:127.0.0.1:8501 -L 8081:127.0.0.1:8081 <your_user>@<server_ip>
```
Then access the UI at http://localhost:8501 in your local browser.

