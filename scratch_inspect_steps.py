import json

transcript_path = "/Users/issam/.gemini/antigravity-ide/brain/1a560cd2-9a41-4bb1-a0fc-06e5a057a0a6/.system_generated/logs/transcript.jsonl"

steps_to_inspect = [43, 1216]

with open(transcript_path, "r", encoding="utf-8") as f:
    for line in f:
        try:
            data = json.loads(line)
            step_idx = data.get("step_index")
            if step_idx in steps_to_inspect:
                print(f"=== STEP {step_idx} ===")
                print(f"type: {data.get('type')}, status: {data.get('status')}")
                content = data.get("content", "")
                print(f"content length: {len(content)}")
                print(f"content starts with: {content[:300]!r}")
                # Print a bit of the middle if it's large
                if len(content) > 1000:
                    print(f"content sample: {content[500:1000]!r}")
        except Exception as e:
            pass
