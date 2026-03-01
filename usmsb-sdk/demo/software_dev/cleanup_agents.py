import requests
import json

# Get all agents
resp = requests.get("http://localhost:8000/agents")
agents = resp.json()
print(f"Found {len(agents)} agents")

# Delete all
for agent in agents:
    agent_id = agent['agent_id']
    try:
        del_resp = requests.delete(f"http://localhost:8000/agents/{agent_id}")
        print(f"Deleted: {agent_id}")
    except Exception as e:
        print(f"Error: {e}")
