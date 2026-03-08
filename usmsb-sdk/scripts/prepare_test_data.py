"""
测试数据准备脚本
用于准备四个模块测试所需的数据
"""

import sqlite3
import json
import os
import time
import hashlib
import secrets

# 数据库路径 - API实际使用的数据库位置
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'src', 'usmsb_sdk', 'data', 'civilization.db')

# API Key 配置
API_KEY_PREFIX = "usmsb"


def generate_api_key(agent_id: str) -> tuple:
    """
    生成符合系统规范的API Key
    返回: (api_key, key_hash, key_prefix)
    """
    # 格式: usmsb_{random_16_hex}_{timestamp_8_hex}
    random_hash = secrets.token_hex(8)  # 16 hex chars
    timestamp = hex(int(time.time()))[2:].zfill(8)  # 8 hex chars
    api_key = f"{API_KEY_PREFIX}_{random_hash}_{timestamp}"
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    key_prefix = api_key[:16]
    return api_key, key_hash, key_prefix

def get_db():
    """获取数据库连接"""
    return sqlite3.connect(DB_PATH)

def init_database():
    """检查数据库表结构是否存在"""
    conn = get_db()
    cursor = conn.cursor()

    print("检查数据库表...")

    # 检查必要的表是否存在
    tables_to_check = ['agents', 'demands', 'services', 'agent_api_keys', 'collaborations', 'workflows', 'agent_wallets']
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = {row[0] for row in cursor.fetchall()}

    missing_tables = []
    for table in tables_to_check:
        if table not in existing_tables:
            missing_tables.append(table)

    if missing_tables:
        print(f"警告: 缺少表: {missing_tables}")
        print("请确保API已初始化数据库")
    else:
        print("所有必要的表都存在")

    return conn


def create_agent_wallets(conn):
    """为测试Agent创建钱包记录（包含质押信息）"""
    cursor = conn.cursor()
    now = time.time() * 1000

    # Agent ID和对应的质押金额、余额
    wallet_data = [
        ('match-supplier-001', 500, 1000),      # staked_amount=500, vibe_balance=1000
        ('match-demand-001', 200, 500),
        ('network-ml-001', 1000, 2000),
        ('network-data-001', 800, 1500),
        ('network-nlp-001', 900, 1800),
        ('network-low-001', 50, 100),
        ('collab-coordinator-001', 500, 1000),
        ('collab-primary-001', 300, 600),
        ('collab-specialist-001', 250, 500),
        ('collab-support-001', 200, 400),
        ('collab-lowstake-001', 50, 100),
        ('sim-agent-001', 200, 400),
        # 前端测试用户的钱包
        ('frontend-test-user', 500, 2000),       # 足够质押发布服务
        ('frontend-demand-test', 200, 1000),     # 足够发布需求
        ('frontend-service-test', 500, 3000),    # 足够质押发布服务
    ]

    for agent_id, staked_amount, vibe_balance in wallet_data:
        wallet_id = f"wallet-{agent_id}"
        cursor.execute('''
            INSERT OR REPLACE INTO agent_wallets
            (id, agent_id, owner_id, wallet_address, agent_address,
             vibe_balance, staked_amount, stake_status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
        ''', (wallet_id, agent_id, f"owner-{agent_id}", f"0x{agent_id}",
              f"0xAgent{agent_id}", vibe_balance, staked_amount, now, now))

    conn.commit()
    print(f"创建了 {len(wallet_data)} 个测试钱包记录")

def create_test_agents(conn):
    """创建测试Agent"""
    cursor = conn.cursor()
    now = time.time() * 1000

    # skills 需要是 List[Dict] 格式: [{"name": "skill_name", "level": 5}]
    agents = [
        # 智能匹配模块测试Agent
        ('match-supplier-001', 'DataAnalyst', 'ai_agent', '数据分析专家',
         '["data_analysis", "python", "pandas", "ml"]',
         '[{"name": "tensorflow", "level": 4}, {"name": "visualization", "level": 5}]',
         'online', 0.85, 500, 1000),
        ('match-demand-001', 'ProjectOwner', 'ai_agent', '项目经理',
         '["project_management"]', '[]',
         'online', 0.75, 200, 500),

        # 网络探索模块测试Agent
        ('network-ml-001', 'MLExpert', 'ai_agent', '机器学习专家',
         '["machine_learning", "deep_learning", "python"]',
         '[{"name": "tensorflow", "level": 5}, {"name": "pytorch", "level": 5}]',
         'online', 0.95, 1000, 2000),
        ('network-data-001', 'DataScientist', 'ai_agent', '数据科学家',
         '["data_analysis", "statistics", "python"]',
         '[{"name": "pandas", "level": 5}, {"name": "numpy", "level": 5}, {"name": "scipy", "level": 4}]',
         'online', 0.88, 800, 1500),
        ('network-nlp-001', 'NLPExpert', 'ai_agent', 'NLP专家',
         '["nlp", "text_analysis", "python"]',
         '[{"name": "spacy", "level": 5}, {"name": "nltk", "level": 4}, {"name": "transformers", "level": 5}]',
         'online', 0.92, 900, 1800),
        ('network-low-001', 'NewbieAgent', 'ai_agent', '新手Agent',
         '["basic_analysis"]', '[{"name": "python", "level": 2}]',
         'online', 0.45, 50, 100),

        # 协作管理模块测试Agent
        ('collab-coordinator-001', 'ProjectCoordinator', 'ai_agent', '项目协调者',
         '["project_management", "coordination"]',
         '[{"name": "planning", "level": 5}, {"name": "communication", "level": 5}]',
         'online', 0.90, 500, 1000),
        ('collab-primary-001', 'BackendDeveloper', 'ai_agent', '后端开发者',
         '["backend_development", "api_design"]',
         '[{"name": "python", "level": 5}, {"name": "fastapi", "level": 4}, {"name": "postgresql", "level": 4}]',
         'online', 0.85, 300, 600),
        ('collab-specialist-001', 'FrontendDeveloper', 'ai_agent', '前端开发者',
         '["frontend_development", "ui_design"]',
         '[{"name": "react", "level": 5}, {"name": "typescript", "level": 4}, {"name": "css", "level": 4}]',
         'online', 0.82, 250, 500),
        ('collab-support-001', 'QAEngineer', 'ai_agent', 'QA工程师',
         '["testing", "quality_assurance"]',
         '[{"name": "pytest", "level": 5}, {"name": "selenium", "level": 4}, {"name": "jest", "level": 4}]',
         'online', 0.78, 200, 400),
        ('collab-lowstake-001', 'JuniorDeveloper', 'ai_agent', '初级开发者',
         '["basic_coding"]', '[{"name": "python", "level": 2}]',
         'online', 0.55, 50, 100),

        # 模拟仿真模块测试Agent
        ('sim-agent-001', 'SimulationAgent', 'ai_agent', '仿真Agent',
         '["task_execution", "planning"]',
         '[{"name": "python", "level": 4}, {"name": "analysis", "level": 4}]',
         'online', 0.85, 200, 400),

        # 前端测试Agent (用于发布需求和服务测试)
        ('frontend-test-user', 'FrontendTestUser', 'ai_agent', '前端测试用户',
         '["testing", "development", "publishing"]',
         '[{"name": "testing", "level": 5}, {"name": "publishing", "level": 5}]',
         'online', 0.90, 500, 2000),  # 500 stake - 足够发布服务
        ('frontend-demand-test', 'FrontendDemandTest', 'ai_agent', '前端需求测试',
         '["demand_publishing", "project_management"]',
         '[{"name": "management", "level": 4}]',
         'online', 0.85, 200, 1000),  # 200 stake
        ('frontend-service-test', 'FrontendServiceTest', 'ai_agent', '前端服务测试',
         '["service_publishing", "gpu", "computing"]',
         '[{"name": "computing", "level": 5}, {"name": "gpu", "level": 5}]',
         'online', 0.88, 500, 3000),  # 500 stake - 足够发布服务
    ]

    for agent in agents:
        cursor.execute('''
            INSERT OR REPLACE INTO agents
            (agent_id, name, agent_type, description, capabilities, skills, status, reputation, stake, balance, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (*agent, now, now))

    conn.commit()
    print(f"创建了 {len(agents)} 个测试Agent")

def create_test_demands(conn):
    """创建测试需求"""
    cursor = conn.cursor()
    now = time.time() * 1000

    demands = [
        ('demand-test-001', 'match-demand-001', '数据分析项目',
         '需要数据清洗和可视化', 'data_analysis', '["python", "pandas", "visualization"]',
         200, 500, 'active'),
    ]

    for demand in demands:
        cursor.execute('''
            INSERT OR REPLACE INTO demands
            (id, agent_id, title, description, category, required_skills, budget_min, budget_max, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (*demand, now))

    conn.commit()
    print(f"创建了 {len(demands)} 个测试需求")

def create_test_services(conn):
    """创建测试服务"""
    cursor = conn.cursor()
    now = time.time() * 1000

    services = [
        ('service-test-001', 'match-supplier-001', '数据分析服务',
         '提供专业数据分析服务', 'data_analysis', '["data_analysis", "python", "ml"]', 100, 'fixed', 'available', 'active'),
    ]

    for service in services:
        cursor.execute('''
            INSERT OR REPLACE INTO services
            (id, agent_id, service_name, description, category, skills, price, price_type, availability, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (*service, now))

    conn.commit()
    print(f"创建了 {len(services)} 个测试服务")

def create_api_keys(conn):
    """为测试Agent创建API Key (使用系统规范的格式和存储方式)"""
    cursor = conn.cursor()
    now = time.time() * 1000

    # 为主要的测试Agent创建API Key
    test_agent_ids = [
        'match-supplier-001',
        'match-demand-001',
        'network-ml-001',
        'network-data-001',
        'network-nlp-001',
        'collab-coordinator-001',
        'collab-primary-001',
        'collab-specialist-001',
        'sim-agent-001',
        # 前端测试用户
        'frontend-test-user',
        'frontend-demand-test',
        'frontend-service-test',
    ]

    # 存储生成的API Key用于显示
    generated_keys = []

    for agent_id in test_agent_ids:
        # 生成符合系统规范的API Key
        api_key, key_hash, key_prefix = generate_api_key(agent_id)

        cursor.execute('''
            INSERT OR REPLACE INTO agent_api_keys
            (id, agent_id, key_hash, key_prefix, name, permissions, level, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (f'key-{agent_id}', agent_id, key_hash, key_prefix,
              f'Test Key for {agent_id}', '["read", "write"]', 0, now))

        generated_keys.append((agent_id, api_key))

    conn.commit()
    print(f"创建了 {len(test_agent_ids)} 个测试API Key")

    return generated_keys

def verify_data(conn, generated_keys):
    """验证数据"""
    cursor = conn.cursor()

    # 统计各表数据量
    tables = ['agents', 'demands', 'services', 'agent_api_keys', 'collaborations', 'workflows']
    print("\n=== 数据验证 ===")

    for table in tables:
        cursor.execute(f'SELECT COUNT(*) FROM {table}')
        count = cursor.fetchone()[0]
        print(f"{table}: {count} 条记录")

    # 显示部分Agent
    print("\n=== 测试Agent列表 ===")
    cursor.execute('SELECT agent_id, name, status, reputation, stake FROM agents LIMIT 15')
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} ({row[2]}, rep={row[3]}, stake={row[4]})")

    # 显示生成的API Key (明文，用于测试)
    print("\n=== 测试API Key (请保存用于测试) ===")
    for agent_id, api_key in generated_keys:
        print(f"  {agent_id}: {api_key}")

def main():
    """主函数"""
    print("=" * 50)
    print("测试数据准备脚本")
    print("=" * 50)

    # 确保data目录存在
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    # 初始化数据库
    conn = init_database()

    # 创建测试数据
    create_test_agents(conn)
    create_agent_wallets(conn)  # 创建钱包记录（质押信息）
    create_test_demands(conn)
    create_test_services(conn)
    generated_keys = create_api_keys(conn)

    # 验证数据
    verify_data(conn, generated_keys)

    conn.close()

    print("\n" + "=" * 50)
    print("测试数据准备完成!")
    print("=" * 50)

    # 将API Keys保存到文件，便于测试使用
    keys_file = os.path.join(os.path.dirname(__file__), '..', 'tests', 'test_api_keys.json')
    os.makedirs(os.path.dirname(keys_file), exist_ok=True)
    with open(keys_file, 'w') as f:
        json.dump(generated_keys, f, indent=2)
    print(f"\nAPI Keys 已保存到: {keys_file}")

if __name__ == '__main__':
    main()
