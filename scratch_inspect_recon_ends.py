with open("reconstructed_from_views.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    line_num = idx + 1
    if line_num > 640:
        if "def " in line or "class " in line or "@router" in line:
            print(f"Line {line_num}: {line.strip()}")
