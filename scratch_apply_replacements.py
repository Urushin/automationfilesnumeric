import json
import os

transcript_path = "/Users/issam/.gemini/antigravity-ide/brain/1a560cd2-9a41-4bb1-a0fc-06e5a057a0a6/.system_generated/logs/transcript.jsonl"
base_pipeline_path = "/Users/issam/Documents/Projets perso/AutomatisationNumericFiles/backend/app/routers/pipeline.py"

with open(base_pipeline_path, "r", encoding="utf-8") as f:
    current_content = f.read()

# Let's collect all edit tool calls on pipeline.py from transcript
edits = []
with open(transcript_path, "r", encoding="utf-8") as f:
    for line in f:
        try:
            data = json.loads(line)
            tool_calls = data.get("tool_calls", [])
            for tc in tool_calls:
                name = tc.get("name")
                if name in ("replace_file_content", "multi_replace_file_content", "write_to_file"):
                    args = tc.get("args", {})
                    target = args.get("TargetFile", "")
                    if "pipeline.py" in target and not target.endswith("extract_pipeline.py") and not target.endswith("reconstruct_pipeline.py") and not target.endswith("reconstruct_better.py"):
                        edits.append({
                            "step_index": data.get("step_index"),
                            "name": name,
                            "args": args
                        })
        except Exception as e:
            pass

print(f"Found {len(edits)} edits on pipeline.py in chronological order.")

for edit in edits:
    step = edit["step_index"]
    name = edit["name"]
    args = edit["args"]
    print(f"Applying Step {step}: {name}")
    if name == "replace_file_content":
        target_content = args.get("TargetContent", "")
        replacement_content = args.get("ReplacementContent", "")
        if target_content in current_content:
            # Check occurrence count
            count = current_content.count(target_content)
            if count > 1 and not args.get("AllowMultiple", False):
                print(f"  [ERROR] TargetContent occurs {count} times, AllowMultiple is False!")
            current_content = current_content.replace(target_content, replacement_content)
            print(f"  [SUCCESS] Replaced. New length: {len(current_content.splitlines())} lines.")
        else:
            print(f"  [WARNING] TargetContent not found in current content!")
            # Let's print a preview of TargetContent to help debug
            print(f"    TargetContent preview: {target_content[:200]!r}")
    elif name == "write_to_file":
        if args.get("Overwrite", False):
            current_content = args.get("CodeContent", "")
            print(f"  [SUCCESS] Overwrote file. New length: {len(current_content.splitlines())} lines.")
        else:
            print(f"  [WARNING] write_to_file without Overwrite=True, skipping.")

with open("reconstructed_via_edits.py", "w", encoding="utf-8") as out:
    out.write(current_content)
print("Saved result to reconstructed_via_edits.py")
