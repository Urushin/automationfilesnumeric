import json
import os

transcript_path = "/Users/issam/.gemini/antigravity-ide/brain/1a560cd2-9a41-4bb1-a0fc-06e5a057a0a6/.system_generated/logs/transcript.jsonl"
pipeline_path = "/Users/issam/Documents/Projets perso/AutomatisationNumericFiles/backend/app/routers/pipeline.py"

# Let's search transcript for VIEW_FILE or edit tool calls of pipeline.py
with open(transcript_path, "r", encoding="utf-8") as f:
    for line in f:
        try:
            data = json.loads(line)
            # Check if this step contains pipeline.py view or write
            content = data.get("content", "")
            if "pipeline.py" in content and "Total Lines" in content:
                print(f"Step {data.get('step_index')}: Found view of pipeline.py with size {len(content)}")
            
            tool_calls = data.get("tool_calls", [])
            for tc in tool_calls:
                args = tc.get("args", {})
                args_str = json.dumps(args)
                if "pipeline.py" in args_str:
                    print(f"Step {data.get('step_index')}: Found tool call {tc.get('name')} with arguments targeting pipeline.py")
        except Exception as e:
            pass

