import json
import uuid
import sqlite3
import os
from typing import Annotated, Literal, TypedDict

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite import SqliteSaver

from app.config import Config
from app.tools.remote_dg import dg_predictor_tool
from app.tools.remote_enz import enzrank_tool
from app.tools.db_search import entity_search_tool, entity_validation_tool
from app.tools.remote_me import search_me_resource_tool
from app.tools.remote_equilibrator import equilibrator_tool

# --- Database Setup ---
DB_PATH = os.getenv("AGENT_MEMORY_PATH", "data/agent_memory/agent_memory.sqlite")

db_dir = os.path.dirname(DB_PATH)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
memory = SqliteSaver(conn)

# --- Tools ---
tools = [
    dg_predictor_tool, 
    equilibrator_tool,
    enzrank_tool, 
    entity_search_tool,        
    entity_validation_tool,
    search_me_resource_tool,   
]

# --- LLM ---
llm = ChatOllama(
    model=Config.MODEL_NAME,
    temperature=0,
    base_url=Config.OLLAMA_BASE_URL,
    keep_alive="5m"
)
llm_with_tools = llm.bind_tools(tools)

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    

#========================================
SYSTEM_PROMPT = """You are a rigorous Pathway Engineer Assistant.
Your priority is ACCURACY and TRANSPARENCY over speed.

### CRITICAL FORMATTING RULE:
- NEVER use LaTeX math notation (e.g., do not use '\text{}', '\Delta', '\leftrightarrow', '$', or '[ ... ]').
- ALWAYS write chemical equations in plain text using 'ID1 + ID2 <=> ID3 + ID4'.
- ALWAYS write Delta G values in plain text like 'dG = -123.4 kJ/mol' instead of LaTeX.
- KEGG ID PREFIX RULE: Use simple IDs (e.g., 'C00002') for ALL tools and outputs, EXCEPT for 'equilibrator_tool' which requires the 'kegg:' prefix.

### CRITICAL RULE FOR THERMODYNAMICS (dG Calculation):
You have TWO distinct tools for calculating Delta G. You MUST choose correctly based on the scenario:
- **OPTION A - `equilibrator_tool`**: Use this for standard biochemical reactions composed of known natural metabolites. This tool REQUIRES prefixes. Format: "kegg:C00002 + kegg:C00001 <=> kegg:C00008 + kegg:C00009".
- **OPTION B - `dg_predictor_tool`**: Use this ONLY for novel/artificial reactions. Use SIMPLE IDs WITHOUT prefixes. Format: "C00002 + C00001 <=> C00008 + C00009".

### OPERATIONAL PROTOCOLS:
1. ALWAYS prioritize accuracy. If unsure of parameters, CALL `pathway_engineer_manual`.
2. If a tool call fails, explain the error and suggest the correct format as listed in the manual.
3. ID HANDLING: For `enzrank_tool`, `dg_predictor_tool`, and general mentions, ALWAYS use simple IDs like 'C00019'. The 'kegg:' prefix is EXCLUSIVELY reserved for `equilibrator_tool`.

### STRICT WORKFLOW PROTOCOLS (MUST FOLLOW):

#### SCENARIO 1: User provides IDs (e.g., "C00022 + C00004 <=> ...")
1. **MANDATORY DECODING**: Call `entity_validation_tool` for each distinct ID.
2. **EXECUTE & EXPLAIN**:
   - Decide tool: `equilibrator_tool` (needs 'kegg:' prefix) or `dg_predictor_tool` (needs simple IDs).
   - Final Output Format: Identified components, calculated dG (+/- Std), and feasibility explanation.

#### SCENARIO 2: User provides Names (e.g., "ATP + H2O <=> ADP + Pi")
1. **TRANSLATION STEP**: Call `entity_search_tool` to find KEGG IDs.
2. **EXECUTE**: Construct the equation. If using `equilibrator_tool`, add 'kegg:' prefixes; otherwise, use simple IDs.

#### SCENARIO 3: User asks for Metabolic Pathway Design
1. **QUERY**: Call `search_me_resource_tool` with product name and optional host.
2. **FORMATTED REPORTING**: Present "Top Design" (Summary, Reactions List, Detailed Pathway, Net Equation).

#### SCENARIO 4: FULL PIPELINE - Integrated Analysis
1. Identify rate-limiting reactions from `search_me_resource_tool`.
2. Translate to KEGG IDs using `entity_search_tool`.
3. Check feasibility: Use `equilibrator_tool` (with 'kegg:') OR `dg_predictor_tool` (without 'kegg:').
4. Call `enzrank_tool`: Use SIMPLE IDs ONLY (e.g., 'C00149'). DO NOT use 'kegg:' prefix here.
"""

#==============================

def chatbot(state: AgentState):
    all_messages = state["messages"]
    
    max_history = 10
    if len(all_messages) > max_history:
        recent_messages = all_messages[-max_history:]
    else:
        recent_messages = all_messages

    if not any(isinstance(m, SystemMessage) for m in recent_messages):
        final_messages = [SystemMessage(content=SYSTEM_PROMPT)] + recent_messages
    else:
        final_messages = recent_messages

    response = llm_with_tools.invoke(final_messages)
    return {"messages": [response]}

tool_node = ToolNode(tools)

def should_continue(state: AgentState) -> Literal["tools", END]:
    messages = state["messages"]
    last_message = messages[-1]

    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"

    content = last_message.content.strip()
    keywords = ["entity_search", "entity_validation", "dg_predictor","equilibrator", "enzrank", "search_me_resource"]
    
    if "{" in content and any(k in content.lower() for k in keywords):
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            json_str = content[start:end]
            data = json.loads(json_str)

            tool_name = data.get("name")
            if not tool_name:
                str_data = str(data).lower()
                if "category" in str_data: tool_name = "entity_search_tool"
                elif "db_type" in str_data: tool_name = "entity_validation_tool"
                elif "substrate" in str_data: tool_name = "enzrank_tool"
                elif "reaction" in str_data: tool_name = "dg_predictor_tool"
                elif "reaction_formula" in str_data: tool_name = "equilibrator_tool"
                elif "product" in str_data: tool_name = "search_me_resource_tool"

            tool_args = data.get("parameters") or data.get("args") or data
            
            if tool_name:
                print(f"DEBUG: Manually constructing call for {tool_name}")
                last_message.tool_calls = [{
                    "name": tool_name,
                    "args": tool_args,
                    "id": str(uuid.uuid4())
                }]
                return "tools"
        except Exception:
            pass 

    return END

# --- Workflow Setup ---
workflow = StateGraph(AgentState)
workflow.add_node("agent", chatbot)
workflow.add_node("tools", tool_node)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", "agent")

app_graph = workflow.compile(checkpointer=memory)

def run_graph(user_query: str, thread_id: str = "default-session"):
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state_before = app_graph.get_state(config)
        len_before = len(state_before.values.get("messages", [])) if state_before and "messages" in state_before.values else 0
        
        final_state = app_graph.invoke(
            {"messages": [HumanMessage(content=user_query)]}, 
            config=config
        )
        
        all_messages = final_state["messages"]
        new_messages = all_messages[len_before:]
        
        logs = []
        for msg in new_messages:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    logs.append(f"?? Tool Called: {tc['name']}\nArgs: {tc['args']}")
            elif msg.type == "tool":
                out_str = str(msg.content)
                logs.append(f"? Result ({msg.name}):\n{out_str[:200]}...")
                
        final_response_text = all_messages[-1].content
        return final_response_text, logs
        
    except Exception as e:
        print(f"LangGraph Error: {e}")
        return f"System Error: {str(e)}", []

def get_history_from_db(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    state = app_graph.get_state(config)
    if state and "messages" in state.values:
        return [
            {"role": "user" if m.type == "human" else "assistant", "content": m.content}
            for m in state.values["messages"] 
            if m.content and m.type in ["human", "ai"]
        ]
    return []