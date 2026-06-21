import os
import json

brain_dir = "/Users/issam/.gemini/antigravity-ide/brain"

for folder in os.listdir(brain_dir):
    folder_path = os.path.join(brain_dir, folder)
    if os.path.isdir(folder_path):
        transcript_path = os.path.join(folder_path, ".system_generated/logs/transcript.jsonl")
        if os.path.exists(transcript_path):
            try:
                with open(transcript_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if "backend/app/routers/pipeline.py" in line:
                            # Let's see if this line has "Total Lines: 2058" or "Total Lines: 21"
                            if "Total Lines:" in line:
                                data = json.loads(line)
                                content = data.get("content", "")
                                idx = content.find("Total Lines:")
                                if idx != -1:
                                    line_count = content[idx:idx+30].split("\n")[0]
                                    print(f"Folder {folder}, Step {data.get('step_index')}: {line_count}")
            except Exception as e:
                pass
