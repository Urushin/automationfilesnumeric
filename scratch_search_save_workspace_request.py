import json

transcript_path = "/Users/issam/.gemini/antigravity-ide/brain/1a560cd2-9a41-4bb1-a0fc-06e5a057a0a6/.system_generated/logs/transcript.jsonl"

with open(transcript_path, "r", encoding="utf-8") as f:
    for line in f:
        if "SaveWorkspaceRequest" in line:
            try:
                data = json.loads(line)
                print(f"Step {data.get('step_index')}: {data.get('type')}")
                content = data.get("content", "")
                if content:
                    print(content[:500])
            except Exception:
                pass
