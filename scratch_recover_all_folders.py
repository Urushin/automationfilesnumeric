import os
import json
import re

brain_dir = "/Users/issam/.gemini/antigravity-ide/brain"

reconstructed_lines = {}
line_pattern = re.compile(r"^\s*(\d+):(?: ?(.*))?$")

print("Scanning all brain folders for pipeline.py views...")

# List all items in brain directory
for folder in os.listdir(brain_dir):
    folder_path = os.path.join(brain_dir, folder)
    if os.path.isdir(folder_path):
        transcript_path = os.path.join(folder_path, ".system_generated/logs/transcript.jsonl")
        if os.path.exists(transcript_path):
            try:
                with open(transcript_path, "r", encoding="utf-8") as f:
                    for line in f:
                        # We must check if the transcript line contains the view_file output of the actual pipeline.py path
                        # File Path is formatted as: File Path: `file:///.../backend/app/routers/pipeline.py`
                        if "routers/pipeline.py`" in line and "Total Lines" in line:
                            data = json.loads(line)
                            content = data.get("content", "")
                            lines_in_view = content.split("\n")
                            for l in lines_in_view:
                                match = line_pattern.match(l)
                                if match:
                                    line_num = int(match.group(1))
                                    line_code = match.group(2) if match.group(2) is not None else ""
                                    # We want to keep the one that matches our target version (length 2154 or 2119 or 2058)
                                    # Actually, let's keep all and print which ones we have
                                    if line_num not in reconstructed_lines:
                                        reconstructed_lines[line_num] = []
                                    reconstructed_lines[line_num].append((folder, line_code))
            except Exception as e:
                pass

print(f"Total unique line numbers found in all views: {len(reconstructed_lines)}")
if reconstructed_lines:
    max_line = max(reconstructed_lines.keys())
    print(f"Max line number: {max_line}")
    # For each line, let's print how many variants we have, and write the most common or newest variant to the file
    # Let's save a file where we choose the code from 1a560cd2 first, then 1be7ffbb, then others
    folder_priority = ["1a560cd2-9a41-4bb1-a0fc-06e5a057a0a6", "1be7ffbb-ff9d-4214-9a90-add72ac9a7a1"]
    
    with open("reconstructed_all_folders.py", "w", encoding="utf-8") as out:
        for i in range(1, max_line + 1):
            if i in reconstructed_lines:
                # Find the best variant
                variants = reconstructed_lines[i]
                chosen_code = None
                # Try priority folders
                for pref in folder_priority:
                    for folder, code in variants:
                        if folder == pref:
                            chosen_code = code
                            break
                    if chosen_code is not None:
                        break
                if chosen_code is None:
                    # Fallback to the first one available
                    chosen_code = variants[0][1]
                out.write(chosen_code + "\n")
            else:
                out.write(f"# MISSING LINE {i}\n")
                
    print("Saved to reconstructed_all_folders.py")
    
    # Calculate missing lines in the reconstructed file
    missing = []
    with open("reconstructed_all_folders.py", "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if line.startswith("# MISSING LINE"):
                missing.append(idx + 1)
    print(f"Number of missing lines in reconstructed_all_folders.py: {len(missing)}")
    if missing:
        # Print ranges of missing lines
        ranges = []
        start = missing[0]
        prev = missing[0]
        for m in missing[1:]:
            if m == prev + 1:
                prev = m
            else:
                ranges.append((start, prev))
                start = m
                prev = m
        ranges.append((start, prev))
        print("Missing ranges:")
        for r in ranges:
            print(f"Lines {r[0]} to {r[1]} ({r[1] - r[0] + 1} lines)")
