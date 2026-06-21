with open("reconstructed_merged.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

with open("modular_endpoints.py", "w", encoding="utf-8") as out:
    # Write from line 1420 to the end
    for idx in range(1419, len(lines)):
        out.write(lines[idx])

print("Saved modular endpoints to modular_endpoints.py")
