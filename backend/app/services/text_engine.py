import os
import requests

def translate_and_optimize_prompt(user_text: str, target_fields: list, instructions: str = None) -> str:
    url = "https://api.mistral.ai/v1/chat/completions"
    
    # Construct precise multi-scoped prompt layout context
    fields_str = ", ".join([f"'{f}'" for f in target_fields])
    system_instruction = (
        f"You are an expert Etsy SEO Optimizer. Update and regenerate ONLY these specific JSON keys: {fields_str}. "
        "Leave any non-specified keys completely unchanged from their original context if provided. "
        "Output strictly a valid JSON object with keys: 'title', 'description', and 'tags' (as an array of strings)."
    )
    
    user_payload_content = f"Original Context Content:\n{user_text}\n\n"
    if instructions and instructions.strip():
        user_payload_content += f"CRITICAL REGENERATION AMENDMENTS TO APPLY:\n{instructions}\n"
        
    payload = {
        "model": "mistral-small-latest",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_payload_content}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2
    }
    
    response = requests.post(url, json=payload, headers={"Authorization": f"Bearer {os.getenv('MISTRAL_API_KEY')}"}, timeout=20)
    return response.json()["choices"][0]["message"]["content"].strip()
