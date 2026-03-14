import json

data = json.load(open('errors.json'))

# Get errors for meta_agent\agent.py
filtered = [e for e in data if 'meta_agent\\agent.py' in e['filename']]

# Sort by row number
filtered.sort(key=lambda x: x['location']['row'])

print(f"Found {len(filtered)} errors in meta_agent/agent.py")
for e in filtered:
    row = e['location']['row']
    col = e['location']['column']
    msg = e['message']
    print(f"{row:4d}:{col:3d} {msg}")
