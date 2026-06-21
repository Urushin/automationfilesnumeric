with open("reconstructed_merged.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

ranges = [
    (761, 771),
    (801, 819),
    (1031, 1051),
    (1081, 1122),
    (1151, 1154),
    (1176, 1199),
    (1366, 1409)
]

for start, end in ranges:
    print(f"\n================ SURROUNDING FOR LINES {start} to {end} ================")
    # Print 5 lines before
    before_start = max(1, start - 5)
    for i in range(before_start, start):
        print(f"{i}: {lines[i-1].rstrip()}")
    print("--- [MISSING REGION] ---")
    for i in range(start, end + 1):
        print(f"{i}: {lines[i-1].rstrip()}")
    print("--- [END MISSING REGION] ---")
    # Print 5 lines after
    after_end = min(len(lines), end + 5)
    for i in range(end + 1, after_end + 1):
        print(f"{i}: {lines[i-1].rstrip()}")
