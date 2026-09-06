# Pathway Agent — Test Run Findings

**Date:** 2026-09-04
**Machine:** macOS (Darwin, Apple Silicon), no Apptainer/Singularity, no GPU — i.e. exactly the "own laptop" path mentioned in `readme.txt` rather than the S9 server.
**Method:** Since `deploy_dev.sh` requires Apptainer (Linux-only) and pre-built `.sif` images that don't exist in this git copy, each of the 6 microservices was instead run **natively** in its own Python virtual environment, wired together with the same ports/env vars `deploy_dev.sh` uses. A real local LLM (`qwen2.5:7b` via Ollama) was pulled and used — nothing below is simulated or hand-written; every quoted response is an actual HTTP response from the running services.

This report is organized by the thematic areas listed in `readme.txt` ("Areas to cover") and cross-referenced against the project's own benchmark categories found in `services/agent-core/evaluation/test_dataset_rich.json` (`EnzRank`, `dGPredictor`, `Database`, `MESearch`, `Neg_*`, `MultiTool_*`, `Capability`, `Greeting`).

---

## 0. Headline Result

| # | Component | readme.txt theme | Could it actually run? | Root cause if not |
|---|---|---|---|---|
| 1 | **Agent Core** (LangGraph + qwen2.5:7b) | orchestration / all themes | ✅ Yes, fully | — |
| 2 | **eQuilibrator** (GSM thermo validation) | GSM simulation validation module | ✅ Yes, fully (after ~12 min first-run download) | — |
| 3 | **SearchMEResource** (strain/host yield lookup) | Strain-selection advisor | ⚠️ Starts, but returns no data | Dataset (Excel files) not in this git copy |
| 4 | **dGPredictor** (pathway ΔG, novel reactions) | Pathway engineering recommender | ❌ No | `openbabel` is Linux-only in `requirements.txt`; fails to import on macOS regardless of model files |
| 5 | **EnzRank** (cofactor/enzyme compatibility) | Cofactor-engineering explorer | ❌ No | Pinned `tensorflow==2.10.0` has **no macOS wheel at all**; CNN weights also absent |
| 6 | **Frontend** (Streamlit UI) | — | Not started (tested via API directly instead — see §6) | n/a |

**Bottom line:** the git copy alone is not runnable end-to-end anywhere, on any OS — `missing_models_and_data.txt` lists **10,720 files** (datasets, `.sif` images, CNN weights, a Redis dump) that exist only on the real deployment. On top of that, two of the four backend tools (`dGPredictor`, `EnzRank`) have a **second, independent** blocker: their pinned dependencies are Linux/x86-only and cannot even be installed on macOS. This second finding would still apply even with the missing data restored, and would also block anyone trying to develop/debug these two services from a Mac.

---

## 1. Deployment & Environment (readme.txt: "can smaller open models run locally and cheaply")

- `ollama pull qwen2.5:7b` (4.7 GB) succeeded and ran locally with no GPU — confirms the project's core premise that a 7B open model is deployable on commodity hardware.
- **eQuilibrator's first-run cost is understated in the README.** The README says the 1.5 GB thermodynamic DB "Loads ... into memory. Takes 1–2 minutes **every time**." In reality, on first run it must first **download** ~1.3 GB from Zenodo (`zenodo.org/api/records/4128543`) before it can load anything — that took **~12 minutes** on this connection, not 1–2 minutes. Only the *load* step is 1–2 minutes; the *download* is a one-time-but-unmentioned cost that will surprise anyone deploying fresh (e.g. on the S9 server, or in CI).
- `services/agent-core/requirements.txt` pins `langchain-ollama==0.1.2`, which pip reports as a **yanked** release ("incorrect core dep — use 0.1.3"). It still installs and works, but should be bumped to avoid relying on a release PyPI has withdrawn.
- The full stack cannot be evaluated end-to-end from this repository alone. `README.md` itself says as much ("Download the full asset package ... Do not use git clone alone") — this run confirms exactly what's missing and why, file-by-file, per service (see table above and `missing_models_and_data.txt`).

## 2. Strain-Selection Advisor (SearchMEResource / "MESearch")

Started `services/SearchMEResource/main.py` directly (no container needed — pure FastAPI + pandas).

- **Good finding:** it does **not** crash on missing data. `MEResourceAgent` loads an empty dataset and the service returns a clean structured error instead of a 500 or a stack trace:
  ```
  POST /query {"product":"succinate","host":"iJN1463","carbon":"D-glucose"}
  → {"status":"error","message":"Yield database is empty"}
  ```
- Through the full agent, the same graceful degradation carries all the way to the final answer — no hallucinated yield numbers were produced for this tool:
  > *"The MEResource database currently does not have any data for the maximum theoretical yield of succinate in the host model iML1515. I recommend trying a different product name or host organism..."*
- **Cannot be substantively evaluated** (host ranking, yield lookup, knockout suggestions) until the `Dataset/*.xlsx` files (the Kim/Kim/Lee *Nature Communications* 2025 supplementary spreadsheets referenced in both `readme.txt` and `README.md`) are restored from the full release tarball.

## 3. Pathway Engineering & GSM Simulation Validation (dGPredictor + eQuilibrator)

**eQuilibrator (works):** After its dependencies installed cleanly with `pip`, it self-downloaded its own real reference thermodynamic database (independent of anything missing from this repo) and came up fully functional:
```
POST /calculate {"reaction_formula": "kegg:C01083 + kegg:C00001 <=> 2 kegg:C00031"}
→ {"status":"success","dG_prime_molar":"-11.45","dG_error":"1.08","units":"kilojoule / mole", ...}
```
Through the agent, this produced a clean, correct, single-tool-call, no-hallucination answer (§6, "clean success" example) — this is the one tool in the whole system that could be fully evaluated as intended on a laptop.

**dGPredictor (blocked, platform issue):** The service *starts* (its startup path doesn't touch model files), but every `/predict` call fails, because `batch_predict.py`'s import chain (`compound_cacher → compound → openbabel`) needs the `openbabel` package, which `requirements.txt` only lists as `openbabel-wheel; sys_platform == 'linux'`. On macOS this dependency is silently skipped by pip, so it's not caught until the first real request:
```
POST /predict {"data": {"R01": "C01083 + C00001 <=> 2 C00031"}}
→ {"error":"Prediction script failed","details":"...ModuleNotFoundError: No module named 'openbabel'\n"}
```
This is a genuine cross-platform gap in the tool itself (not just missing data) — anyone trying to run or extend dGPredictor off Linux hits this immediately.

## 4. Cofactor-/Enzyme-Engineering Explorer (EnzRank)

Not testable at all, for two independent reasons:
1. **Missing data:** `missing_models_and_data.txt` confirms the CNN weights (`CNN_model_final/Final_model.model`) are not in this repo.
2. **Missing platform support:** `pip install tensorflow==2.10.0` (the version pinned in `requirements.txt`) fails outright on this machine — no matching wheel exists for macOS/arm64 at that version at all:
   ```
   ERROR: Could not find a version that satisfies the requirement tensorflow==2.10.0
   ERROR: No matching distribution found for tensorflow==2.10.0
   ```
   Even ignoring the missing weights, this service can only ever be developed/tested inside its Apptainer container or on a Linux x86 machine with an old CUDA-era TF build — worth flagging to whoever picks this component up next.

## 5. Compound/Entity Lookup (KEGG/UniProt live APIs — the `Database` benchmark category)

This tool needs no local data or model at all (it calls live public REST APIs), so it was the most representative test of "real" behavior:
```
Query: "Search for information on the compound Geranyl diphosphate"
→ correctly resolved to KEGG compound C00341 in a single tool call, no hallucination,
   and the agent proactively offered a sensible next step (run equilibrator_tool / enzrank_tool on it).
```
This worked well and is a good sign for the "retrieval/numeric accuracy" metric in `readme.txt` when the underlying data source is actually reachable.

## 6. Agent Reliability & Hallucination Rate (Agent Core / LangGraph)

This is the most important section, since it's the one component that was 100% testable and is central to `readme.txt`'s evaluation metrics ("hallucination rate," "agent reliability," "ranking consistency").

**Non-tool queries (Greeting / Capability / Neg_Gen categories) — all correct, fast (~1.3s), no unnecessary tool calls:**
- *"Hi there."* → simple greeting back, asked how it can help.
- *"Tell me about your skills."* → accurately listed its 5 real tools by name.
- *"Who is the current president of the United States?"* → correctly declined ("I'm here to assist with biochemical and metabolic engineering queries...") instead of guessing or hallucinating a name.

**Clean tool success (eQuilibrator available) — correct on the first try:**
- *"Calculate the Gibbs free energy for ... C01083 + C00001 <=> 2 C00031"* → one correct tool call, result reproduced exactly and correctly interpreted ("...ΔG' is negative [so] the reaction is spontaneous"). 17.5s round trip (CPU-only 7B model).

**⚠️ Hallucination when a required tool is unavailable — the key negative finding.** With `dGPredictor`/`eQuilibrator` both down, the same dG query led to:
- 3 redundant, identical retries of `dg_predictor_tool` and 2 of `equilibrator_tool` (no backoff/retry limit visible in the transcript before giving up on the *real* tool),
- then the model **fabricated a number anyway**, substituting an unrelated standard reaction (ATP hydrolysis, ≈ ‑30.5 kJ/mol) as a stand-in for the actual query and presenting it as a "rough estimate," rather than clearly stopping at "I cannot compute this — the tool is unavailable."

**⚠️ Failed negative-test case (`Neg_Enz` benchmark category) — reveals a second, sharper hallucination mode.** The project's own eval set includes *"Rank the catalytic affinity between Glucose and ATP"* with `expected_tool: null` (i.e., the correct behavior is to recognize this isn't a valid enzyme+substrate pair and decline). The live agent instead:
1. Looked up both compounds via `entity_search_tool` (reasonable),
2. Then called `enzrank_tool` passing the **compound IDs as the enzyme sequence field** (`{"enzyme": "C00031", "substrate": "C00002"}`) — a category-confused tool call the negative test is specifically designed to catch,
3. Got a connection error (service down), and then **generated a confident, factually wrong fallback explanation**, misattributing EC numbers (e.g. calling EC 6.1.1.6 "hexokinase" — hexokinase is actually EC 2.7.1.1; calling EC 6.3.1.23 "ATP synthase" — ATP synthase is EC 7.1.2.2) while still concluding "the catalytic affinity ... is significant."

**Interpretation:** the agent's honesty is **inconsistent** — it correctly refused an out-of-scope general-knowledge question (President of the US) but did not apply the same discipline to an out-of-scope *tool* question, and its behavior on tool failure ranges from an honest "connection error, please retry" (seen once) to a fabricated numeric/factual answer presented with unwarranted confidence (seen twice). Since `readme.txt` names hallucination rate as a primary evaluation metric, the `Neg_*` categories in the existing benchmark (50/145 rows) look like exactly the right lever to quantify this — this run only sampled a handful by hand.

## 7. Latency (readme.txt metric)

Rough, CPU-only, single-machine numbers (not a proper benchmark, just what was observed):

| Query type | Wall time |
|---|---|
| No tool call (greeting/capability/general-knowledge refusal) | ~1.3 s |
| Single successful tool call (entity search or eQuilibrator) | ~6–18 s |
| Failed tool → retries → fallback hallucination | ~15–32 s |

Take-away: latency scales with the number of (often redundant) tool-call attempts, so fixing the retry/hallucination behavior in §6 would likely improve both hallucination rate *and* latency together.

---

## Recommendations / Next Steps

1. **Get the full asset tarball or S9 server access** (as `readme.txt` line 24 already anticipates) — this is a hard blocker for evaluating `SearchMEResource`, `dGPredictor`, and `EnzRank` at all; nothing about this run can substitute for that.
2. **Fix the two macOS/platform blockers independently of the data problem**: swap `openbabel-wheel` for a conda-forge `openbabel` install (or document Linux-only support explicitly) for dGPredictor; document that EnzRank requires Linux + the pinned TF 2.10 (or upgrade past it) for anyone without the Apptainer image.
3. **Add a tool-call retry cap + an explicit "tool unavailable, cannot compute" terminal state** in `graph.py` — the repeated identical retries followed by a fabricated fallback answer (§6) is the single most actionable/highest-value fix relative to the project's own stated hallucination-rate metric.
4. **Run the existing 145-row `test_dataset_rich.json` through `run_eval.py`/`score_eval.py`** once qwen2.5:7b + at least one working tool are available — the negative (`Neg_*`) categories in particular look under-tested and, based on the one sample tried here, may be failing.
5. **Correct the README's eQuilibrator timing claim** ("1–2 minutes every time") to mention the one-time ~1.3 GB / ~10–15 minute first-run download separately from the fast in-memory reload.

---
*Generated from a live run against qwen2.5:7b (Ollama), agent-core, eQuilibrator, and SearchMEResource on this machine; dGPredictor and EnzRank findings are based on direct install/run attempts plus `missing_models_and_data.txt`.*
