#!/usr/bin/env python3
"""Fix duplicate timeout parameters in sandbox tests"""

import re

file_path = "tests/unit/test_sandbox/test_code_sandbox.py"

# Read the file
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace duplicate timeout=30, timeout=30 with single timeout=30
content = re.sub(r', timeout=30, timeout=30\)', ', timeout=30)', content)

# Write the modified content back
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed duplicate timeout parameters")
