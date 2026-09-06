# -*- coding: utf-8 -*-
import os
import glob
import json
import time
import pandas as pd
import requests
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = os.path.join(SCRIPT_DIR, 'reports')
OLLAMA_URL = 'http://127.0.0.1:11434/api/generate'
MODEL_NAME = 'llama3.1' 

def get_latest_csv(directory):
    search_pattern = os.path.join(directory, 'eval_report_*.csv')
    files = [f for f in glob.glob(search_pattern) if "scored_" not in os.path.basename(f)]
    if not files:
        raise FileNotFoundError(f"No raw eval_report_*.csv file found in: {directory}")
    
    files.sort(key=os.path.getmtime)
    return files[-1]

def judge_llm_scoring(query, llm_output, expected_tool, actual_tools):
    if pd.isna(query) or pd.isna(llm_output):
        return {"accuracy": 0, "reasoning": 0, "completeness": 0, "thought": "Missing data"}

    prompt = f"""
    You are an expert AI evaluator specialized in Biotechnology and Cheminformatics. 
    Your task is to critique the Agent's performance based on a user query.

    [Context]
    User Query: {query}
    Expected Tool: {expected_tool}
    Tools Used by Agent: {actual_tools}
    Agent Final Response: {llm_output}

    [Evaluation Criteria] (Score each from 1-5)
    1. Accuracy: Is the response directly aligned with the user's query and contextually accurate?
    2. Reasoning: Does the agent explain its logic clearly? Is the step-by-step process sound?
    3. Completeness: Did the agent answer all parts of the user request?

    [Output Requirement]
    Return ONLY a JSON object with the following keys:
    "accuracy": integer,
    "reasoning": integer,
    "completeness": integer,
    "total_score": integer (sum of above, max 15),
    "improvement_suggestion": string (brief reasoning on how to improve the agent)

    JSON Output:
    """

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        
        if response.status_code != 200:
            return {"accuracy": 0, "reasoning": 0, "completeness": 0, "total_score": 0, "improvement_suggestion": f"API Error {response.status_code}"}
            
        result_json = json.loads(response.json().get("response", "{}"))
        return result_json
            
    except Exception as e:
        print(f"\n[Warning] Scoring failed for a row: {e}")
        return {"accuracy": 0, "reasoning": 0, "completeness": 0, "total_score": 0, "improvement_suggestion": "Internal parsing error"}

def main():
    print("==========================================")
    print(f"   Judge LLM: {MODEL_NAME} Scoring Mode")
    print("==========================================")
    
    try:
        latest_csv = get_latest_csv(REPORT_DIR)
        print(f"[Info] Found latest raw report: {os.path.basename(latest_csv)}")
        
        df = pd.read_csv(latest_csv)
        total_rows = len(df)
        
        print(f"[Info] Processing {total_rows} rows. This may take a while...")
        
        scored_data = []
        for index, row in df.iterrows():
            print(f" > Progress: {index + 1}/{total_rows} | Case: {row['id']}", end='\r')
            
            scores = judge_llm_scoring(
                row['query'], 
                row['raw_llm_output'],
                row.get('expected_tool', 'N/A'),
                row.get('actual_tools', 'N/A')
            )
            
            combined_row = row.to_dict()
            combined_row.update({
                'judge_accuracy': scores.get('accuracy', 0),
                'judge_reasoning': scores.get('reasoning', 0),
                'judge_completeness': scores.get('completeness', 0),
                'judge_total_score': scores.get('total_score', 0),
                'improvement_suggestion': scores.get('improvement_suggestion', '')
            })
            scored_data.append(combined_row)
            
        result_df = pd.DataFrame(scored_data)
        base_name = os.path.basename(latest_csv)
        output_filename = os.path.join(REPORT_DIR, f"scored_final_{base_name}")
        result_df.to_csv(output_filename, index=False)
        
        print(f"\n[Success] Scoring completed!")
        print(f"[Success] Detailed report saved to: {output_filename}")

        print("\n" + "="*20 + " SUMMARY " + "="*20)
        avg_total = result_df['judge_total_score'].mean()
        avg_acc = result_df['judge_accuracy'].mean()
        avg_reason = result_df['judge_reasoning'].mean()
        
        print(f"Total Cases Evaluated: {total_rows}")
        print(f"Avg Total Score      : {avg_total:.2f} / 15.00")
        print(f"Avg Accuracy (1-5)   : {avg_acc:.2f}")
        print(f"Avg Reasoning (1-5)  : {avg_reason:.2f}")
        
        print("\nTop 3 Critical Areas for Improvement:")
        weak_cases = result_df.nsmallest(3, 'judge_total_score')
        for i, row in weak_cases.iterrows():
            print(f"- Case {row['id']} (Score {row['judge_total_score']}): {row['improvement_suggestion'][:100]}...")
        print("="*49 + "\n")

    except Exception as e:
        print(f"\n[Fatal Error] {e}")

if __name__ == "__main__":
    main()