import json
import re

transcript_path = "/Users/issam/.gemini/antigravity-ide/brain/1a560cd2-9a41-4bb1-a0fc-06e5a057a0a6/.system_generated/logs/transcript.jsonl"
reconstructed_lines = {}

# We match: optional whitespace, digits, colon, optional space, and then the rest of the line.
line_pattern = re.compile(r"^\s*(\d+):(?: ?(.*))?$")

with open(transcript_path, "r", encoding="utf-8") as f:
    for line in f:
        try:
            data = json.loads(line)
            # Check content of the step (which contains the tool output displayed to the agent)
            content = data.get("content", "")
            if "pipeline.py" in content and "Total Lines" in content:
                lines = content.split("\n")
                for l in lines:
                    match = line_pattern.match(l)
                    if match:
                        line_num = int(match.group(1))
                        line_code = match.group(2) if match.group(2) is not None else ""
                        reconstructed_lines[line_num] = line_code
            
            # Let's also check if there is any tool_calls/output or responses in the JSON
            # In some logs, the tool output is in other fields of the JSON object. Let's print them if we find any.
        except Exception as e:
            pass

print(f"Total reconstructed lines: {len(reconstructed_lines)}")
if reconstructed_lines:
    max_line = max(reconstructed_lines.keys())
    print(f"Max line number: {max_line}")
    missing = [i for i in range(1, max_line + 1) if i not in reconstructed_lines]
    print(f"Number of missing lines: {len(missing)}")
    
    # Save the reconstructed file
    with open("reconstructed_from_views.py", "w", encoding="utf-8") as out:
        for i in range(1, max_line + 1):
            out.write(reconstructed_lines.get(i, f"# MISSING LINE {i}") + "\n")
    print("Saved to reconstructed_from_views.py")
