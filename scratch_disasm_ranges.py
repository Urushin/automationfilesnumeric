import re

disasm_path = "/Users/issam/Documents/Projets perso/AutomatisationNumericFiles/pipeline_disassembly.txt"

# Missing ranges:
ranges = [
    (648, 669),
    (746, 819),
    (1011, 1199),
    (1366, 1409),
    (1916, 1919),
    (1951, 1969),
    (2004, 2004)
]

# We want to find lines in the disassembly file.
# The format of line number in disassembly is typically starting a block:
# " 648           ..." or " 1011          ..." at the start of a line.
# Let's write a parser that extracts instructions grouped by line number.

line_instrs = {}
current_line = None

# A typical line number starts with optional spaces followed by digits, then spaces, then instruction name.
# e.g., " 648           LOAD_FAST                0 (creation_id)"
# Or if it's a continuation of the same line, it starts with spaces, then no line number, just offset:
# "              LOAD_FAST                1 (theme)"
line_num_pattern = re.compile(r"^\s*(\d+)\s+([A-Z_]+.*)$")
offset_pattern = re.compile(r"^\s*(\d+)?\s+([A-Z_]+.*)$")

with open(disasm_path, "r", encoding="utf-8") as f:
    for line in f:
        line_str = line.rstrip()
        if not line_str:
            continue
        
        # Check if line starts with a line number
        # Note: dis output format:
        # "  55           0 LOAD_CONST               1 (2)"
        # "              2 STORE_FAST               0 (x)"
        # Let's match a line number. It is usually at the very beginning.
        parts = line_str.split()
        if len(parts) >= 2:
            # If the first part is a number and is not followed immediately by another number (which would be offset)
            # Actually, standard dis output for python 3.13:
            # "  L.  55:      0: LOAD_CONST               1 (2)" or similar?
            # Let's check how the disassembly file looks by reading a few lines.
            pass

# Let's just print lines from the disassembly file that contain the line numbers we want!
with open(disasm_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for start, end in ranges:
    print(f"=== Disassembly for lines {start} to {end} ===")
    found = False
    for line in lines:
        # Match line number at the start of line (e.g. " 648 ")
        # In Python 3.13, the line number might be formatted like:
        # " 648           ..." or "L. 648"
        # Let's do a regex search for the line number as a word at the beginning of the line
        match = re.search(r"^\s*(" + str(start) + r"|" + "|".join(str(i) for i in range(start, end+1)) + r")\b", line)
        if match:
            print(line.rstrip())
            found = True
    if not found:
        print("No disassembly found in this range.")
