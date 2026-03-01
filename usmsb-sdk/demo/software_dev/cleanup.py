import requests
import json

# Get all agents
resp = requests.get("http://localhost:8000/agents")
agents = resp.json()

print(f"Found {len(agents)} agents")

# Delete all except test-agent
for agent in agents:
    agent_id = agent['agent_id']
    if agent_id != 'test-agent-1':
        try:
            del_resp = requests.delete(f"http://localhost:8000/agents/{agent_id}")
            print(f"Deleted: {agent_id} ({agent.get('name', 'unknown')}) - {del_resp.status_code}")
        except Exception as e:
            print(f"Error: {e}")

# Verify
resp = requests.get("http://localhost:8000/agents")
agents = resp.json()
print(f"\nRemaining agents: {len(agents)}")
for a in agents:
    print(f"  - {a['agent_id']}: {a['name']}")
