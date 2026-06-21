import json
import os

transcript_path = "/Users/issam/.gemini/antigravity-ide/brain/1a560cd2-9a41-4bb1-a0fc-06e5a057a0a6/.system_generated/logs/transcript.jsonl"

with open(transcript_path, "r", encoding="utf-8") as f:
    for line in f:
        try:
            data = json.loads(line)
            tool_calls = data.get("tool_calls", [])
            for tc in tool_calls:
                name = tc.get("name")
                if name in ("write_to_file", "replace_file_content", "multi_replace_file_content"):
                    args = tc.get("args", {})
                    target = args.get("TargetFile", "")
                    if "pipeline.py" in target:
                        print(f"Step {data.get('step_index')}: {name} on {target}")
                        content = args.get("CodeContent") or args.get("ReplacementContent") or ""
                        print(f"  Content length: {len(content)}")
                        if len(content) > 1000:
                            print(f"  Content starts with: {content[:200]}")
                            # Let's save this content to a separate file so we can view it
                            filename = f"write_step_{data.get('step_index')}.py"
                            with open(filename, "w", encoding="utf-8") as out:
                                out.write(content)
                            print(f"  Saved to {filename}")
        except Exception as e:
            print("Error:", e)
