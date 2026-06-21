import json

transcript_path = "/Users/issam/.gemini/antigravity-ide/brain/1a560cd2-9a41-4bb1-a0fc-06e5a057a0a6/.system_generated/logs/transcript.jsonl"

# Let's search for "1015:" or "1050:" in the transcript.
targets = ["1015:", "1050:", "1100:", "1380:", "1955:"]

with open(transcript_path, "r", encoding="utf-8") as f:
    for line in f:
        for t in targets:
            if t in line:
                try:
                    data = json.loads(line)
                    print(f"Found target '{t}' in step {data.get('step_index')}")
                except Exception:
                    print(f"Found target '{t}' in raw line: {line[:200]}")
