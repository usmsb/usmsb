import json

data = json.load(open('errors.json'))

# Get errors for a specific file
target_file = input("Enter file pattern (or press Enter for all): ").strip()

if target_file:
    filtered = [e for e in data if target_file.replace('/', '\\') in e['filename']]
else:
    filtered = data

# Sort by row number
filtered.sort(key=lambda x: x['location']['row'])

for e in filtered[:100]:  # Limit to first 100
    row = e['location']['row']
    col = e['location']['column']
    msg = e['message']
    fn = e['filename'].split('\\')[-1]
    print(f"{row:4d}:{col:3d} {msg}")
