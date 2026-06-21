import os

base_pipeline_path = "/Users/issam/Documents/Projets perso/AutomatisationNumericFiles/backend/app/routers/pipeline.py"
reconstructed_path = "/Users/issam/Documents/Projets perso/AutomatisationNumericFiles/reconstructed_from_views.py"

with open(base_pipeline_path, "r", encoding="utf-8") as f:
    base_lines = f.readlines()

with open(reconstructed_path, "r", encoding="utf-8") as f:
    recon_lines = f.readlines()

filled_lines = []
missing_after_647 = []

for idx, line in enumerate(recon_lines):
    line_num = idx + 1
    if line.startswith(f"# MISSING LINE {line_num}"):
        # Check if we can fill it from base lines
        if line_num <= len(base_lines):
            filled_lines.append(base_lines[line_num - 1])
        else:
            filled_lines.append(line)
            missing_after_647.append(line_num)
    else:
        filled_lines.append(line)

print(f"Filled from base: {len(recon_lines) - len(missing_after_647) - recon_lines.count('# MISSING LINE')} lines.")
print(f"Still missing after line 647: {len(missing_after_647)} lines.")
if missing_after_647:
    # Print ranges of missing lines after 647
    ranges = []
    start = missing_after_647[0]
    prev = missing_after_647[0]
    for m in missing_after_647[1:]:
        if m == prev + 1:
            prev = m
        else:
            ranges.append((start, prev))
            start = m
            prev = m
    ranges.append((start, prev))
    print("Missing ranges after 647:")
    for r in ranges:
        print(f"Lines {r[0]} to {r[1]} ({r[1] - r[0] + 1} lines)")

with open("reconstructed_filled.py", "w", encoding="utf-8") as out:
    out.writelines(filled_lines)
print("Saved to reconstructed_filled.py")
