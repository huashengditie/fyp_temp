# -*- coding: utf-8 -*-
import sys
import os
import json
import time
import sqlite3
import pandas as pd

# ==========================================================
# 1. Environment and Path Configuration
# ==========================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

MEMORY_DIR = os.path.abspath(os.path.join(current_dir, "../../../data/agent_memory"))
DB_PATH = os.path.join(MEMORY_DIR, "agent_memory.sqlite")

# ==========================================================
# 2. Import Agent Graph
# ==========================================================
try:
    from app.agents.graph import app_graph
    print(f"Successfully imported 'app_graph' from app.agents.graph")
except ImportError as e:
    print(f"Error: Failed to import 'app_graph'. Details: {e}")
    sys.exit(1)

class BioAgentEvaluator:
    def __init__(self, dataset_path, output_dir):
        self.dataset_path = dataset_path
        self.output_dir = output_dir
        self.results = []
        os.makedirs(output_dir, exist_ok=True)
        
        if not os.path.exists(dataset_path):
            print(f"Error: Dataset not found at {dataset_path}")
            sys.exit(1)
            
        with open(dataset_path, 'r', encoding='utf-8') as f:
            self.test_cases = json.load(f)

    def clear_agent_memory(self):
        if not os.path.exists(DB_PATH):
            os.makedirs(MEMORY_DIR, exist_ok=True)
            return

        conn = None
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            
            cursor.execute("PRAGMA foreign_keys = OFF;")
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            for table in tables:
                table_name = table[0]
                if not table_name.startswith("sqlite_"):
                    cursor.execute(f"DELETE FROM {table_name};")
            
            conn.commit()
        except sqlite3.Error as e:
            print(f"  [Memory Clear Warning] SQLite error: {e}")
        finally:
            if conn:
                conn.close()

    def run(self):
        total_cases = len(self.test_cases)
        print(f"\n=== Starting Evaluation | Total Cases: {total_cases} ===")
        print(f"Database Path: {DB_PATH}")
        print(f"Isolation Mode: Table Truncation + Unique Thread IDs")
        
        timestamp = int(time.time())
        csv_file = os.path.join(self.output_dir, f"eval_report_{timestamp}.csv")

        for index, case in enumerate(self.test_cases):
            self.clear_agent_memory()

            print(f"[{index+1}/{total_cases}] Case ID: {case['id']}...", end="", flush=True)
            
            start_ts = time.time()
            error_msg = None
            actual_tools = []
            final_answer = ""

            try:
                config = {"configurable": {"thread_id": f"eval_{case['id']}"}}
                inputs = {"messages": [("user", case['query'])]}
                
                response = app_graph.invoke(inputs, config=config)
                
                messages = response.get('messages', [])
                if messages:
                    final_answer = messages[-1].content
                    
                    for msg in messages:
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            for tc in msg.tool_calls:
                                actual_tools.append(tc['name'])
            
            except Exception as e:
                error_msg = str(e)
                final_answer = f"CRASH: {error_msg}"

            latency = round(time.time() - start_ts, 2)
            
            self.results.append({
                "id": case['id'],
                "category": case.get('category', 'Unknown'),
                "query": case['query'],
                "latency_sec": latency,
                "expected_tool": case.get('expected_tool') or case.get('expected_tools'),
                "actual_tools": ",".join(actual_tools),
                "raw_llm_output": final_answer,
                "error": error_msg if error_msg else ""
            })
            
            print(f" Done ({latency}s)")

        df = pd.DataFrame(self.results)
        df.to_csv(csv_file, index=False, encoding='utf-8')
        print(f"\n[Success] Evaluation complete. Report: {csv_file}")

# ==========================================================
# 3. Execution Entry Point
# ==========================================================
if __name__ == "__main__":
    dataset_file = os.path.join(current_dir, "test_dataset_rich.json")
    report_folder = os.path.join(current_dir, "reports")
    
    evaluator = BioAgentEvaluator(dataset_file, report_folder)
    evaluator.run()