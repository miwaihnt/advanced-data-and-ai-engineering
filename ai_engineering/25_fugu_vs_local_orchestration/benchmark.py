import time
import json
import os
from typing import Dict, Any, List
from dotenv import load_dotenv

# Load environmental variables from .env file
load_dotenv()
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

# Import custom agents and generator
from data_generator import get_test_cases, Order
from agent_local import run_local_agent
from agent_fugu import run_fugu_agent, SCHEMA_DESC

# ==========================================
# 1. Single LLM Runner (Control Group)
# ==========================================

def run_single_llm(corrupted_json: str, model_name: str = "qwen2.5:3b") -> Dict[str, Any]:
    """
    Attempts to clean JSON in a single shot using Ollama. No validation loops.
    """
    llm = ChatOllama(model=model_name, temperature=0.0)
    
    prompt_text = f"""You are a data validation assistant.
Your task is to fix a corrupted JSON string so that it conforms strictly to the target schema.

{SCHEMA_DESC}

### Corrupted JSON:
{corrupted_json}

Return ONLY the final repaired JSON. Do not write markdown wrappers (```json), explanations, or notes.
"""
    
    prompt = ChatPromptTemplate.from_template("{prompt_text}")
    chain = prompt | llm
    
    history = ["Single LLM: Sending request..."]
    try:
        response = chain.invoke({"prompt_text": prompt_text})
        fixed_content = response.content.strip()
        
        # Cleanup markdown wrappers
        if fixed_content.startswith("```json"):
            fixed_content = fixed_content[7:]
        if fixed_content.startswith("```"):
            fixed_content = fixed_content[3:]
        if fixed_content.endswith("```"):
            fixed_content = fixed_content[:-3]
        fixed_content = fixed_content.strip()
        
        history.append(f"Single LLM: Response received: {fixed_content}")
        
        # Validation test
        Order.model_validate_json(fixed_content)
        history.append("Single LLM validation success.")
        
        return {
            "success": True,
            "final_json": fixed_content,
            "attempts": 1,
            "history": history,
            "error": None
        }
    except Exception as e:
        err_str = str(e)
        history.append(f"Single LLM validation failed: {err_str}")
        return {
            "success": False,
            "final_json": corrupted_json,
            "attempts": 1,
            "history": history,
            "error": err_str
        }


# ==========================================
# 2. Main Benchmark Runner
# ==========================================

def run_benchmark(model_name: str = "qwen2.5:3b", use_mock_fugu: bool = True):
    cases = get_test_cases()
    results = []

    print("=" * 60)
    print(" STARTING FUGU vs LANGGRAPH ORCHESTRATION BENCHMARK")
    print(f" Local Model: {model_name}")
    print(f" Fugu Mode: {'MOCK' if use_mock_fugu else 'REAL API'}")
    print("=" * 60)

    for case in cases:
        print(f"\n>>> Running: {case['name']}...")
        corrupted_json = case["corrupted_json"]
        
        # --- 1. Single LLM ---
        start_time = time.time()
        res_single = run_single_llm(corrupted_json, model_name=model_name)
        time_single = time.time() - start_time
        
        # --- 2. Local SDK Loop (Ollama) ---
        start_time = time.time()
        res_local = run_local_agent(corrupted_json, model_name=model_name, max_attempts=3)
        time_local = time.time() - start_time
        
        # --- 3. Sakana Fugu ---
        start_time = time.time()
        res_fugu = run_fugu_agent(corrupted_json, mock=use_mock_fugu)
        time_fugu = time.time() - start_time
        
        results.append({
            "case_name": case["name"],
            "single": {
                "success": res_single["success"],
                "attempts": res_single["attempts"],
                "time": time_single,
                "error": res_single["error"]
            },
            "local_sdk": {
                "success": res_local["success"],
                "attempts": res_local["attempts"],
                "time": time_local,
                "error": res_local["error"]
            },
            "fugu": {
                "success": res_fugu["success"],
                "attempts": res_fugu["attempts"],
                "time": time_fugu,
                "error": res_fugu["error"]
            }
        })
        
    print_markdown_table(results)
    save_results_to_readme(results, model_name, use_mock_fugu)


# ==========================================
# 3. Utility: Print & Save Results
# ==========================================

def print_markdown_table(results: List[Dict[str, Any]]):
    print("\n" + "=" * 60)
    print(" BENCHMARK RESULTS")
    print("=" * 60 + "\n")
    
    headers = [
        "Test Case", 
        "Single LLM (Success / Time / Loops)", 
        "Local SDK Loop (Success / Time / Loops)", 
        "Sakana Fugu (Success / Time / Loops)"
    ]
    
    row_format = "| {:<35} | {:<25} | {:<25} | {:<25} |"
    print(row_format.format(*headers))
    print("|" + "-" * 37 + "|" + "-" * 27 + "|" + "-" * 27 + "|" + "-" * 27 + "|")
    
    for r in results:
        single_str = f"{'✅ PASS' if r['single']['success'] else '❌ FAIL'} / {r['single']['time']:.2f}s / {r['single']['attempts']}"
        local_str = f"{'✅ PASS' if r['local_sdk']['success'] else '❌ FAIL'} / {r['local_sdk']['time']:.2f}s / {r['local_sdk']['attempts']}"
        fugu_str = f"{'✅ PASS' if r['fugu']['success'] else '❌ FAIL'} / {r['fugu']['time']:.2f}s / {r['fugu']['attempts']}"
        
        print(row_format.format(r["case_name"], single_str, local_str, fugu_str))
    print("\n" + "=" * 60)

def save_results_to_readme(results: List[Dict[str, Any]], model_name: str, use_mock_fugu: bool):
    """Generates the Markdown table to be referenced in README.md"""
    md = []
    md.append(f"### Benchmark Run Results (Local Model: `{model_name}`, Fugu API: `{'MOCK' if use_mock_fugu else 'REAL'}`)\n")
    md.append("| Test Case | Single LLM (Ollama) | Local SDK Loop (Ollama) | Sakana Fugu API |")
    md.append("| :--- | :---: | :---: | :---: |")
    
    for r in results:
        single_str = f"{'✅ PASS' if r['single']['success'] else '❌ FAIL'}<br>Time: {r['single']['time']:.2f}s<br>Loops: {r['single']['attempts']}"
        local_str = f"{'✅ PASS' if r['local_sdk']['success'] else '❌ FAIL'}<br>Time: {r['local_sdk']['time']:.2f}s<br>Loops: {r['local_sdk']['attempts']}"
        fugu_str = f"{'✅ PASS' if r['fugu']['success'] else '❌ FAIL'}<br>Time: {r['fugu']['time']:.2f}s<br>Loops: {r['fugu']['attempts']}"
        
        md.append(f"| {r['case_name']} | {single_str} | {local_str} | {fugu_str} |")
        
    print("\n[INFO] Copy-paste this Markdown table to your README.md:\n")
    print("\n".join(md))
    print("\n" + "=" * 60)


if __name__ == "__main__":
    # Determine if API key exists. If not, use mock mode for Fugu
    api_key_exists = "SAKANA_API_KEY" in os.environ
    run_benchmark(model_name="qwen2.5:3b", use_mock_fugu=not api_key_exists)
