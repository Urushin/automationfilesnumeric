with open("reconstructed_merged.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("=== Lines 110 to 125 ===")
for i in range(110, 126):
    if i <= len(lines):
        print(f"{i}: {lines[i-1].strip()}")

print("=== Lines 595 to 605 ===")
for i in range(595, 606):
    if i <= len(lines):
        print(f"{i}: {lines[i-1].strip()}")
