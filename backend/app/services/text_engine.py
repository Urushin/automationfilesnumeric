import os
import requests

def translate_and_optimize_prompt(user_text: str, target_fields: list, instructions: str = None) -> str:
    url = "https://api.mistral.ai/v1/chat/completions"
    
    # Enforce a dual-language system mapping both FR and EN schemas
    target_fields_str = ", ".join([f"'{f}'" for f in target_fields])
    system_instruction = (
        "You are an expert bilingual Etsy SEO specialist. You must strictly output a valid JSON object.\n"
        "The object must contain two main root structures: 'fr' and 'en'.\n"
        "Each root structure must have exactly these keys: 'title', 'description', and 'tags' (array of strings).\n"
        f"You are allowed to regenerate or update ONLY these sub-fields based on the user request: {target_fields_str}.\n"
        "If a field is not in that list, preserve its original content identically from the provided bilingual context.\n"
        "Ensure titles are optimized for click-through rate, tags contain relevant search vectors, and formatting is clear.\n"
        "Output strictly a valid JSON object with exactly the structure: {\"fr\": {\"title\": \"...\", \"description\": \"...\", \"tags\": [...]}, \"en\": {\"title\": \"...\", \"description\": \"...\", \"tags\": [...]}}"
    )
    
    user_payload_content = f"Current Existing Bilingual Data Context (FR and EN):\n{user_text}\n\n"
    if instructions and instructions.strip():
        user_payload_content += f"USER AMENDMENTS TO APPLY TO TARGET FIELDS:\n{instructions}\n"
        
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
