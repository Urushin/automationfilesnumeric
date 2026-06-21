import os
import json
import re

brain_dir = "/Users/issam/.gemini/antigravity-ide/brain"

# We will group views by their stated "Total Lines" count.
# For each group, we keep a mapping of line_num -> code.
version_lines = {}
line_pattern = re.compile(r"^\s*(\d+):(?: ?(.*))?$")

print("Scanning all brain folders and grouping by Total Lines...")

for folder in os.listdir(brain_dir):
    folder_path = os.path.join(brain_dir, folder)
    if os.path.isdir(folder_path):
        transcript_path = os.path.join(folder_path, ".system_generated/logs/transcript.jsonl")
        if os.path.exists(transcript_path):
            try:
                with open(transcript_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if "backend/app/routers/pipeline.py" in line or "routers/pipeline.py" in line:
                            if "Total Lines:" in line:
                                data = json.loads(line)
                                content = data.get("content", "")
                                # Find Total Lines:
                                m_lines = re.search(r"Total Lines:\s*(\d+)", content)
                                if m_lines:
                                    total_lines = int(m_lines.group(1))
                                    if total_lines not in version_lines:
                                        version_lines[total_lines] = {}
                                    
                                    lines_in_view = content.split("\n")
                                    for l in lines_in_view:
                                        match = line_pattern.match(l)
                                        if match:
                                            line_num = int(match.group(1))
                                            line_code = match.group(2) if match.group(2) is not None else ""
                                            version_lines[total_lines][line_num] = line_code
            except Exception as e:
                pass

print("Scan complete. Version statistics:")
for total_lines, lines_map in sorted(version_lines.items()):
    missing = [i for i in range(1, total_lines + 1) if i not in lines_map]
    print(f"Version with Total Lines {total_lines}: Reconstructed {len(lines_map)} / {total_lines} lines. Missing {len(missing)} lines.")
    
    # Save the reconstructed file if it is almost complete
    if len(missing) < 50:
        filename = f"reconstructed_v{total_lines}.py"
        with open(filename, "w", encoding="utf-8") as out:
            for i in range(1, total_lines + 1):
                out.write(lines_map.get(i, f"# MISSING LINE {i}") + "\n")
        print(f"  Saved to {filename}")
