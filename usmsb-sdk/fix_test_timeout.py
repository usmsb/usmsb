#!/usr/bin/env python3
"""Fix missing timeout parameter in sandbox tests"""

import re

file_path = "tests/unit/test_sandbox/test_code_sandbox.py"

# Read the file
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern 1: sandbox.execute("...") - multiline with triple quotes
# Need to find sandbox.execute(...) and add timeout=30 if not present

# Simple approach: Find all sandbox.execute calls and ensure they have timeout=
# This is a bit tricky due to multiline strings

# Let's do a more targeted approach - find lines that end with ) and are sandbox.execute calls
# that don't have timeout= or timeout =

# We'll process line by line
lines = content.split('\n')
result_lines = []
i = 0

while i < len(lines):
    line = lines[i]
    result_lines.append(line)

    # Check if this line starts with result = await sandbox.execute(" and doesn't have timeout=
    if 'result = await sandbox.execute(' in line and 'timeout=' not in line:
        # Check if it's a multi-line string (triple quote)
        if '"""' in line or "'''" in line:
            # Find the closing """ and the closing )
            # Continue adding lines until we find the closing )
            j = i + 1
            while j < len(lines):
                result_lines.append(lines[j])
                if ')' in lines[j] and ('"""' in lines[j] or "'''" in lines[j]):
                    # Found the end, now modify this line to add timeout= before the closing )
                    current_line = result_lines[-1]
                    # Add timeout=30 before the closing )
                    modified_line = current_line.rstrip()[:-1] + ', timeout=30)'
                    result_lines[-1] = modified_line
                    i = j
                    break
                j += 1
            else:
                # Didn't find closing, just continue
                i = j - 1
        elif 'timeout=' not in line:
            # Single line, just add timeout=30 before the closing )
            # Check if line ends with ) after a closing quote
            # Remove the line we just added and add modified version
            result_lines.pop()
            # Find the position of the last )
            last_paren = line.rfind(')')
            if last_paren != -1:
                # Insert timeout=30 before the last )
                modified_line = line[:last_paren] + ', timeout=30' + line[last_paren:]
                result_lines.append(modified_line)

    i += 1

# Write the modified content back
with open(file_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(result_lines))

print("Fixed test file")
