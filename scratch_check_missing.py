import json
import re

reconstructed_lines = {}
line_pattern = re.compile(r"^\s*(\d+):(?: ?(.*))?$")

transcript_path = "/Users/issam/.gemini/antigravity-ide/brain/1a560cd2-9a41-4bb1-a0fc-06e5a057a0a6/.system_generated/logs/transcript.jsonl"

with open(transcript_path, "r", encoding="utf-8") as f:
    for line in f:
        try:
            data = json.loads(line)
            content = data.get("content", "")
            if "pipeline.py" in content and "Total Lines" in content:
                lines = content.split("\n")
                for l in lines:
                    match = line_pattern.match(l)
                    if match:
                        line_num = int(match.group(1))
                        line_code = match.group(2) if match.group(2) is not None else ""
                        reconstructed_lines[line_num] = line_code
        except Exception:
            pass

if reconstructed_lines:
    max_line = max(reconstructed_lines.keys())
    missing = [i for i in range(1, max_line + 1) if i not in reconstructed_lines]
    
    # Print missing ranges
    if missing:
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
