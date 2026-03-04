"""
超级管理员 (superadmin) 权限测试脚本 - 使用curl

测试目标：验证 superadmin 角色拥有全部37项权限
测试用户: 0x382B71e8b425CFAaD1B1C6D970481F440458Abf8
"""

import subprocess
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000"
SUPERADMIN_WALLET = "0x382B71e8b425CFAaD1B1C6D970481F440458Abf8"
TEST_WALLET_HUMAN = "0x5777e716DA114cA5c146E40908399Eb2ef032cb0"

GREEN = '\033[92m'
RED = '\033[91m'
RESET = '\033[0m'

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def add_pass(self, name, detail=""):
        self.passed += 1
        self.results.append(f"{GREEN}✓ PASS{RESET} - {name} {detail}")

    def add_fail(self, name, detail=""):
        self.failed += 1
        self.results.append(f"{RED}✗ FAIL{RESET} - {name} {detail}")

def curl_get(endpoint):
    """执行curl GET请求"""
    try:
        result = subprocess.run(
            ['curl', '-s', f"{BASE_URL}{endpoint}"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout:
            try:
                return json.loads(result.stdout)
            except:
                return result.stdout
        return None
    except Exception as e:
        return None

def curl_post(endpoint, data):
    """执行curl POST请求"""
    try:
        result = subprocess.run(
            ['curl', '-s', '-X', 'POST', '-H', 'Content-Type: application/json',
             '-d', json.dumps(data), f"{BASE_URL}{endpoint}"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout:
            try:
                return json.loads(result.stdout)
            except:
                return result.stdout
        return None
    except Exception as e:
        return None

def test_user_info(result: TestResult):
    """测试1: 获取用户信息"""
    print("\n" + "="*50)
    print("测试1: 获取用户信息")
    print("="*50)

    data = curl_get(f"/api/meta-agent/user/{SUPERADMIN_WALLET}")
    if data and isinstance(data, dict):
        role = data.get("role")
        permissions = data.get("permissions", [])

        if role == "superadmin":
            result.add_pass("用户角色验证", f"role={role}")
        else:
            result.add_fail("用户角色验证", f"expected=superadmin, got={role}")

        perm_count = len(permissions)
        if perm_count >= 37:
            result.add_pass("权限数量验证", f"共{perm_count}项权限")
        else:
            result.add_fail("权限数量验证", f"expected>=37, got={perm_count}")

        print(f"  角色: {role}")
        print(f"  权限数量: {perm_count}")
    else:
        result.add_fail("用户信息API", "无法获取数据")

def test_permission_check(result: TestResult):
    """测试2: 权限检查API"""
    print("\n" + "="*50)
    print("测试2: 权限检查API")
    print("="*50)

    test_permissions = [
        "platform:admin", "platform:config", "platform:deploy",
        "node:start", "node:stop", "node:monitor", "node:config",
        "agent:register", "agent:unregister", "agent:manage", "agent:service",
        "wallet:create", "wallet:bind", "blockchain:stake", "blockchain:vote", "blockchain:govern",
        "data:query", "data:write", "data:admin",
        "chat:basic", "chat:admin",
        "system:health", "system:metrics", "system:logs",
        "workspace", "sandbox", "browser", "network",
        "npm:public", "npm:install", "npm:run", "npm:global", "npm:danger",
        "git:read", "git:write", "git:push", "git:clone", "git:force", "git:danger"
    ]

    passed_count = 0
    for perm in test_permissions:
        data = curl_get(f"/api/meta-agent/permission/check-tool/{SUPERADMIN_WALLET}/{perm}")
        if data and isinstance(data, dict) and data.get("allowed"):
            passed_count += 1

    print(f"  通过: {passed_count}/{len(test_permissions)}")
    if passed_count >= 37:
        result.add_pass("权限检查完成", f"{passed_count}/39项通过")
    else:
        result.add_fail("权限检查", f"通过{passed_count}项少于预期")

def test_permission_stats(result: TestResult):
    """测试3: 权限统计API"""
    print("\n" + "="*50)
    print("测试3: 权限统计API")
    print("="*50)

    data = curl_get("/api/meta-agent/permission/stats")
    if data and isinstance(data, dict):
        print(f"  统计数据: {json.dumps(data, ensure_ascii=False)}")
        result.add_pass("权限统计API")
    else:
        result.add_fail("权限统计API")

def test_tools_endpoint(result: TestResult):
    """测试4: 工具列表API"""
    print("\n" + "="*50)
    print("测试4: 工具列表API")
    print("="*50)

    data = curl_get("/api/meta-agent/tools")
    if data and isinstance(data, list):
        tool_count = len(data)
        print(f"  可用工具数量: {tool_count}")
        result.add_pass("工具列表API", f"{tool_count}个工具")
    else:
        result.add_fail("工具列表API")

def test_chat_endpoint(result: TestResult):
    """测试5: 对话API"""
    print("\n" + "="*50)
    print("测试5: 对话API (chat:basic)")
    print("="*50)

    data = curl_post("/api/meta-agent/chat", {
        "wallet_address": SUPERADMIN_WALLET,
        "message": "测试超级管理员对话功能",
        "context": {}
    })
    if data and isinstance(data, dict) and "response" in data:
        print(f"  响应成功")
        result.add_pass("对话API")
    else:
        result.add_fail("对话API")

def test_health_endpoint(result: TestResult):
    """测试6: 健康检查API"""
    print("\n" + "="*50)
    print("测试6: 健康检查API (system:health)")
    print("="*50)

    data = curl_get("/api/health")
    if data and isinstance(data, dict):
        print(f"  健康状态: {data.get('status')}")
        result.add_pass("健康检查API")
    else:
        result.add_fail("健康检查API")

def test_history_endpoint(result: TestResult):
    """测试7: 历史记录API"""
    print("\n" + "="*50)
    print("测试7: 历史记录API (chat:admin)")
    print("="*50)

    data = curl_get(f"/api/meta-agent/history/{SUPERADMIN_WALLET}")
    if data and isinstance(data, list):
        print(f"  历史记录数量: {len(data)}")
        result.add_pass("历史记录API")
    else:
        result.add_fail("历史记录API")

def test_human_permission(result: TestResult):
    """测试8: 对比human角色权限"""
    print("\n" + "="*50)
    print("测试8: 对比human角色权限 (验证权限隔离)")
    print("="*50)

    data = curl_get(f"/api/meta-agent/user/{TEST_WALLET_HUMAN}")
    if data and isinstance(data, dict):
        role = data.get("role")
        permissions = data.get("permissions", [])
        perm_count = len(permissions)

        print(f"  human角色: {role}")
        print(f"  human权限数量: {perm_count}")

        if perm_count < 37:
            result.add_pass("权限隔离验证", f"human({perm_count}) < superadmin(37)")
        else:
            result.add_fail("权限隔离验证")

        if "platform:admin" not in permissions:
            result.add_pass("human无platform:admin", "权限隔离正确")
        else:
            result.add_fail("human不应有platform:admin")
    else:
        result.add_fail("human用户信息")

def test_key_tools(result: TestResult):
    """测试9: 关键工具权限测试"""
    print("\n" + "="*50)
    print("测试9: 关键工具权限测试")
    print("="*50)

    test_cases = [
        ("chat:basic", "general_response"),
        ("workspace", "read_file"),
        ("sandbox", "execute_python"),
        ("system:health", "health_check"),
        ("agent:register", "register_agent"),
        ("wallet:create", "create_wallet"),
    ]

    for perm, tool in test_cases:
        data = curl_get(f"/api/meta-agent/permission/check-tool/{SUPERADMIN_WALLET}/{perm}")
        if data and data.get("allowed"):
            result.add_pass(f"工具 {tool}", f"权限={perm}")
        else:
            result.add_fail(f"工具 {tool}")

def main():
    print("\n" + "="*60)
    print("超级管理员 (superadmin) 权限测试")
    print("="*60)
    print(f"测试用户: {SUPERADMIN_WALLET}")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    result = TestResult()

    test_user_info(result)
    test_permission_check(result)
    test_permission_stats(result)
    test_tools_endpoint(result)
    test_chat_endpoint(result)
    test_health_endpoint(result)
    test_history_endpoint(result)
    test_human_permission(result)
    test_key_tools(result)

    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    print(f"通过: {GREEN}{result.passed}{RESET}")
    print(f"失败: {RED}{result.failed}{RESET}")
    print(f"总计: {result.passed + result.failed}")

    print("\n" + "-"*60)
    print("详细结果:")
    print("-"*60)
    for r in result.results:
        print(f"  {r}")

    # 保存报告
    report = {
        "test_time": datetime.now().isoformat(),
        "wallet": SUPERADMIN_WALLET,
        "role": "superadmin",
        "passed": result.passed,
        "failed": result.failed,
        "total": result.passed + result.failed,
        "results": result.results
    }

    report_file = f"tests/superadmin_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n测试报告已保存至: {report_file}")

    sys.exit(0 if result.failed == 0 else 1)

if __name__ == "__main__":
    main()
