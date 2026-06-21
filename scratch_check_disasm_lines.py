import re

disasm_path = "/Users/issam/Documents/Projets perso/AutomatisationNumericFiles/pipeline_disassembly.txt"
lines_found = set()

# In dis output, line numbers are typically at the beginning of the lines as integers.
# Let's extract the first word if it consists of digits.
with open(disasm_path, "r", encoding="utf-8") as f:
    for line in f:
        parts = line.strip().split()
        if parts:
            # Check if the first part is digits
            if parts[0].isdigit():
                lines_found.add(int(parts[0]))
            # Or if it's like "L. 648" or something
            elif len(parts) > 1 and parts[0] == "L." and parts[1].isdigit():
                lines_found.add(int(parts[1]))

print(f"Total unique line numbers found in disassembly: {len(lines_found)}")
if lines_found:
    print(f"Min line number: {min(lines_found)}")
    print(f"Max line number: {max(lines_found)}")
    # Print list of sorted line numbers in a compact way
    sorted_lines = sorted(list(lines_found))
    # Print ranges
    ranges = []
    start = sorted_lines[0]
    prev = sorted_lines[0]
    for m in sorted_lines[1:]:
        if m == prev + 1:
            prev = m
        else:
            ranges.append((start, prev))
            start = m
            prev = m
    ranges.append((start, prev))
    print("Line ranges present in disassembly:")
    for r in ranges:
        print(f"Lines {r[0]} to {r[1]} ({r[1] - r[0] + 1} lines)")
