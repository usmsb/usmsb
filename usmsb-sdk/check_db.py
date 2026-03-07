import sqlite3

conn = sqlite3.connect(r'C:/Users/1/Documents/vibecode/usmsb-sdk/data/meta_agent_tasks.db')
cursor = conn.cursor()

# Check schema
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tables:", tables)

for table in tables:
    cursor.execute(f"PRAGMA table_info({table})")
    columns = cursor.fetchall()
    print(f"\n{table} columns:")
    for col in columns:
        print(f"  {col[1]} ({col[2]}) - {col[0]}")
    print()

# Check tasks
print("\nTasks:")
cursor.execute("SELECT task_id, wallet_address, status, created_at FROM task_progress ORDER by created_at DESC LIMIT 5")
tasks = cursor.fetchall()
for task in tasks:
    print(f"  Task ID: {task[0]}, Wallet: {task[1]}, Status: {task[2]}, Created: {task[3]}")

conn.close()
