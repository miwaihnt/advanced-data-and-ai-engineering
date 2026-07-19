from typing import Dict, Any, List, Optional
import json
from openai import OpenAI
from data_generator import Order

# ==========================================
# 1. LLM Prompt Template
# ==========================================

FIX_PROMPT = """You are a professional data engineering assistant.
Your task is to fix a corrupted JSON string so that it conforms strictly to the target Pydantic schema.

### Target Pydantic Schema Fields & Descriptions:
- order_id: (str) Unique order ID
- customer: (Customer object) Containing:
  - customer_id: (str) Unique customer ID
  - email: (str) Valid email address
  - membership: (str) Must be exactly one of "VIP", "Regular", or "Guest"
- items: (List of Item objects) Each containing:
  - item_id: (str) Unique item ID
  - price: (float) Must be greater than 0
  - quantity: (int) Must be at least 1
- total_amount: (float) Must match the sum of (price * quantity) of all items
- order_date: (datetime) Date and time of the order in ISO format (e.g. 2026-07-14T09:00:00Z)

### Corrupted JSON:
{current_json}

### Validation Errors Occurred:
{error_message}

### Instructions:
1. Carefully analyze the validation errors and the corrupted JSON.
2. Fix all errors:
   - Map wrong keys to target field names (e.g. `qty` -> `quantity`, `ord_number` -> `order_id`, `cust_id` -> `customer_id`).
   - Clean data types (e.g., convert string numbers "two" -> 2, "10.00 USD" -> 10.0).
   - Standardize inputs (e.g., validate and reconstruct email, enforce membership casing like "regular_customer" -> "Regular").
   - Restructure flattened JSON into nested structure if the "customer" field is missing.
   - Recalculate `total_amount` if it does not equal the sum of item prices multiplied by quantities.
3. Return ONLY the valid JSON object. Do not include markdown code block syntax (like ```json ... ```), explanations, notes, or any other wrapper text. Just raw JSON.
"""

# ==========================================
# 2. Pure Python Loop using OpenAI SDK (Ollama Local API)
# ==========================================

def run_local_agent(corrupted_json: str, model_name: str = "qwen2.5:3b", max_attempts: int = 3) -> Dict[str, Any]:
    """
    Cleans the corrupted JSON using a pure Python loop.
    Utilizes OpenAI's SDK pointed to Ollama's local compatibility endpoint.
    """
    # Configure client to point to Ollama's local OpenAI-compatible endpoint
    client = OpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama"  # Ollama doesn't require a key, but OpenAI SDK expects a non-empty string
    )

    current_json = corrupted_json
    attempts = 0
    history = []
    is_valid = False
    error_message = None

    while attempts < max_attempts:
        history.append(f"State: Entering validation (Attempt {attempts + 1})")
        
        # 1. Validation Phase (Local Pydantic)
        try:
            validated_obj = Order.model_validate_json(current_json)
            # Re-serialize to get normalized formatting
            normalized_json = validated_obj.model_dump_json()
            history.append("Validation Success: JSON matches target schema.")
            is_valid = True
            current_json = normalized_json
            error_message = None
            break  # Exit loop immediately upon success
        except Exception as e:
            error_message = str(e)
            history.append(f"Validation Failure: {error_message}")
            
        # 2. Check retry budget
        if attempts + 1 >= max_attempts:
            break
            
        # 3. LLM Repair Phase (OpenAI SDK calling Local Ollama)
        history.append(f"State: Invoking Ollama via OpenAI SDK ({model_name}) to fix errors...")
        prompt = FIX_PROMPT.format(
            current_json=current_json,
            error_message=error_message
        )
        
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
            )
            fixed_content = response.choices[0].message.content.strip()
            
            # Cleanup markdown blocks if any
            if fixed_content.startswith("```json"):
                fixed_content = fixed_content[7:]
            if fixed_content.startswith("```"):
                fixed_content = fixed_content[3:]
            if fixed_content.endswith("```"):
                fixed_content = fixed_content[:-3]
            fixed_content = fixed_content.strip()
            
            history.append(f"LLM generated fix response: {fixed_content}")
            current_json = fixed_content
        except Exception as e:
            history.append(f"LLM Invocation Failed: {str(e)}")
            
        attempts += 1

    return {
        "success": is_valid,
        "final_json": current_json,
        "attempts": attempts,
        "history": history,
        "error": error_message
    }

if __name__ == "__main__":
    from data_generator import get_test_cases
    cases = get_test_cases()
    
    # Test on Case 1
    print("Testing Case 1 (Severe Type Coercion) with OpenAI SDK (Ollama Local)...")
    res = run_local_agent(cases[4]["corrupted_json"], model_name="qwen2.5:3b")
    print("\n--- RUN RESULTS ---")
    print(f"Success: {res['success']}")
    print(f"Attempts: {res['attempts']}")
    print(f"Final JSON: {res['final_json']}")
    print("\nHistory:")
    for step in res["history"]:
        print(f" - {step}")
