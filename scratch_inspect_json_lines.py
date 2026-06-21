import json

transcript_path = "/Users/issam/.gemini/antigravity-ide/brain/1a560cd2-9a41-4bb1-a0fc-06e5a057a0a6/.system_generated/logs/transcript.jsonl"

targets = ["1015:", "1050:", "1100:", "1380:", "1955:"]

with open(transcript_path, "r", encoding="utf-8") as f:
    for line in f:
        # We check if any target is in the line and if "pipeline.py" is in the line
        if "pipeline.py" in line:
            for t in targets:
                if t in line:
                    try:
                        data = json.loads(line)
                        print(f"Step {data.get('step_index')}: found {t}")
                        content = data.get("content", "")
                        tool_calls = data.get("tool_calls", [])
                        if content and t in content:
                            print(f"  In content. Length={len(content)}")
                        for tc in tool_calls:
                            args_str = json.dumps(tc.get("args", {}))
                            if t in args_str:
                                print(f"  In tool call {tc.get('name')} args")
                    except Exception as e:
                        pass
