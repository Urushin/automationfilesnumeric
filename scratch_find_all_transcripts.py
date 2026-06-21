import os
import json

brain_dir = "/Users/issam/.gemini/antigravity-ide/brain"
matching_steps = []

for folder in os.listdir(brain_dir):
    folder_path = os.path.join(brain_dir, folder)
    if os.path.isdir(folder_path):
        transcript_path = os.path.join(folder_path, ".system_generated/logs/transcript.jsonl")
        if os.path.exists(transcript_path):
            # Check the file
            try:
                with open(transcript_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if "backend/app/routers/pipeline.py" in line and '"name":"write_to_file"' in line:
                            data = json.loads(line)
                            # Let's see if this write tool call has a large body
                            tool_calls = data.get("tool_calls", [])
                            for tc in tool_calls:
                                args = tc.get("args", {})
                                if "pipeline.py" in args.get("TargetFile", ""):
                                    content = args.get("CodeContent", "")
                                    print(f"Found write to pipeline.py in folder {folder}, step {data.get('step_index')}, len={len(content)}")
                                    if len(content) > 50000:
                                        # Save this!
                                        out_name = f"recovered_pipeline_{folder}_{data.get('step_index')}.py"
                                        with open(out_name, "w", encoding="utf-8") as out:
                                            out.write(content)
                                        print(f"  Saved to {out_name}")
            except Exception as e:
                pass

print("Done scanning.")
