#!/usr/bin/env python3
"""Script to identify files with most E501 errors and help fix them."""
import subprocess
import re
from collections import defaultdict

# Run ruff check to get E501 errors
result = subprocess.run(
    ["ruff", "check", "src/", "--select=E501"],
    capture_output=True,
    text=True,
    cwd="C:\\Users\\1\\Documents\\vibecode"
)

# Parse output to count errors per file (ruff outputs to stdout)
output = result.stdout + result.stderr
file_counts = defaultdict(int)
for line in output.split("\n"):
    if "Line too long" in line:
        # Extract file path
        match = re.search(r"-->\s+([^:]+):", line)
        if match:
            file_counts[match.group(1)] += 1

# Sort by count
sorted_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)

print(f"Total files with E501 errors: {len(sorted_files)}")
print(f"Total E501 errors: {sum(file_counts.values())}")
print("\nTop 20 files with most errors:")
for file, count in sorted_files[:20]:
    print(f"  {count:4d} errors: {file}")
