# Markdown File Compilation

An index of every `.md` file in this repository, with a one-sentence description of what each one contains.

## Project Root

| File | What it contains |
|---|---|
| [`README.md`](README.md) | The top-level project README — architecture/port table, deployment instructions (Apptainer + Ollama), sample queries, and evaluation-script usage for the Pathway Agent system. |
| [`FINDINGS.md`](FINDINGS.md) | A test report from actually running the system on this machine (no Apptainer/GPU), documenting which services worked, which failed and why, and a real, reproduced example of the agent hallucinating when a tool was unavailable. |
| [`CONTRIBUTIONS.md`](CONTRIBUTIONS.md) | A summary of Shen Xintong's FYP thesis contributions (the LangGraph agent, the anti-hallucination Search-Verify-Compute protocol, the 6-service integration, and the 140-case LLM benchmark), cross-checked against the actual codebase. |
| [`FILE_COMPILATION.md`](FILE_COMPILATION.md) | This file — an index of every markdown file in the repo and what it's for. |

## Service-Level Docs

| File | What it contains |
|---|---|
| [`services/dGPredictor/README.md`](services/dGPredictor/README.md) | Upstream dGPredictor tool's own setup guide — Python/RDKit/OpenBabel installation steps and how to run its standalone Streamlit demo and group-contribution ΔG prediction pipeline. |
| [`services/EnzRank/README.md`](services/EnzRank/README.md) | A minimal Hugging Face Spaces config header for EnzRank's legacy Streamlit demo (title, emoji, SDK version) — not a usage guide. |
| [`services/agent-core/app/agents/graph_diagram.md`](services/agent-core/app/agents/graph_diagram.md) | A developer-facing diagram and node/edge reference for the actual LangGraph state machine in `graph.py`, including its ReAct loop and the manual JSON tool-call fallback for models that don't call tools natively. |
| [`services/frontend/md/database_links.md`](services/frontend/md/database_links.md) | A short list of external reference links (KEGG, BiGG, SABIO-RK, Rhea) shown in the frontend UI's "Knowledge Base" sidebar for ID lookup and data verification. |
| [`services/frontend/md/tool_description.md`](services/frontend/md/tool_description.md) | Frontend-UI copy describing what the dGPredictor and EnzRank tools do, their inputs/outputs, and their source-paper references. |

*(`PROJECT_EXPLAINED.ipynb` and `readme.txt` are not included above as they are not `.md` files.)*
