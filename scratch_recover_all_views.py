import os
import json
import re

brain_dir = "/Users/issam/.gemini/antigravity-ide/brain"
folders = ["1be7ffbb-ff9d-4214-9a90-add72ac9a7a1", "1a560cd2-9a41-4bb1-a0fc-06e5a057a0a6"]

reconstructed_lines = {}
line_pattern = re.compile(r"^\s*(\d+):(?: ?(.*))?$")

for folder in folders:
    folder_path = os.path.join(brain_dir, folder)
    transcript_path = os.path.join(folder_path, ".system_generated/logs/transcript.jsonl")
    if os.path.exists(transcript_path):
        print(f"Reading from folder {folder}...")
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    content = data.get("content", "")
                    if ("app/routers/pipeline.py" in content or "routers/pipeline.py" in content) and "Total Lines" in content:
                        lines = content.split("\n")
                        for l in lines:
                            match = line_pattern.match(l)
                            if match:
                                line_num = int(match.group(1))
                                line_code = match.group(2) if match.group(2) is not None else ""
                                # If the line was already reconstructed, we prefer the one from 1a560cd2 (the newer conversation)
                                if line_num not in reconstructed_lines or folder == "1a560cd2-9a41-4bb1-a0fc-06e5a057a0a6":
                                    reconstructed_lines[line_num] = line_code
                except Exception as e:
                    pass

print(f"Total reconstructed lines: {len(reconstructed_lines)}")
if reconstructed_lines:
    max_line = max(reconstructed_lines.keys())
    print(f"Max line number: {max_line}")
    missing = [i for i in range(1, max_line + 1) if i not in reconstructed_lines]
    print(f"Number of missing lines: {len(missing)}")
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

    with open("reconstructed_merged.py", "w", encoding="utf-8") as out:
        for i in range(1, max_line + 1):
            out.write(reconstructed_lines.get(i, f"# MISSING LINE {i}") + "\n")
    print("Saved to reconstructed_merged.py")
