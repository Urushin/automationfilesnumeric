with open("reconstructed_merged.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

in_missing = False
start_missing = 0

for idx, line in enumerate(lines):
    line_num = idx + 1
    is_missing = line.startswith("# MISSING LINE")
    
    if is_missing:
        if not in_missing:
            in_missing = True
            start_missing = line_num
    else:
        if in_missing:
            print(f"Lines {start_missing} to {line_num - 1}: MISSING")
            in_missing = False
        
        # Print non-missing line if it is a function definition or decorator
        strip_line = line.strip()
        if strip_line.startswith("def ") or strip_line.startswith("class ") or strip_line.startswith("@router"):
            print(f"Line {line_num}: {strip_line}")

if in_missing:
    print(f"Lines {start_missing} to {len(lines)}: MISSING")
