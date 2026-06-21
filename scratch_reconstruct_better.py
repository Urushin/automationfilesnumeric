import json
import re

transcript_path = "/Users/issam/.gemini/antigravity-ide/brain/1a560cd2-9a41-4bb1-a0fc-06e5a057a0a6/.system_generated/logs/transcript.jsonl"
reconstructed_lines = {}

# We match: optional whitespace, digits, colon, optional single space, and then the rest of the line.
# Example: "  123:     def foo():" -> group(1) = "123", group(2) = "    def foo():"
# Example: "123:" -> group(1) = "123", group(2) = ""
line_pattern = re.compile(r"^\s*(\d+):(?: ?(.*))?$")

with open(transcript_path, "r", encoding="utf-8") as f:
    for line in f:
        try:
            data = json.loads(line)
            content = data.get("content", "")
            if "pipeline.py" in content and "Total Lines" in content:
                lines = content.split("\n")
                for l in lines:
                    match = line_pattern.match(l) # Do NOT strip before matching, so we can see spaces
                    if match:
                        line_num = int(match.group(1))
                        line_code = match.group(2) if match.group(2) is not None else ""
                        reconstructed_lines[line_num] = line_code
        except Exception as e:
            pass

print(f"Reconstructed {len(reconstructed_lines)} lines.")
if reconstructed_lines:
    max_line = max(reconstructed_lines.keys())
    print(f"Max line number: {max_line}")
    # Let's count how many missing lines there are
    missing = [i for i in range(1, max_line + 1) if i not in reconstructed_lines]
    print(f"Number of missing lines: {len(missing)}")
    if len(missing) < 50:
        print(f"Missing line numbers: {missing}")
    
    with open("reconstructed_better.py", "w", encoding="utf-8") as out:
        for i in range(1, max_line + 1):
            out.write(reconstructed_lines.get(i, f"# MISSING LINE {i}") + "\n")
    print("Saved to reconstructed_better.py")
