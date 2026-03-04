"""
超级管理员 (superadmin) 权限测试脚本

测试目标：验证 superadmin 角色拥有全部37项权限，并能正确调用相关API

测试用户: 0x382B71e8b425CFAaD1B1C6D970481F440458Abf8
"""

import requests
import json
import sys
from datetime import datetime

# 配置
BASE_URL = "http://localhost:8000"
SUPERADMIN_WALLET = "0x382B71e8b425CFAaD1B1C6D970481F440458Abf8"
TEST_WALLET_HUMAN = "0x5777e716DA114cA5c146E40908399Eb2ef032cb0"

# 颜色输出
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
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

def test_user_info(result: TestResult):
    """测试1: 获取用户信息"""
    print("\n" + "="*50)
    print("测试1: 获取用户信息")
    print("="*50)

    try:
        resp = requests.get(f"{BASE_URL}/api/meta-agent/user/{SUPERADMIN_WALLET}", timeout=10)
        data = resp.json()

        if resp.status_code == 200:
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
            print(f"  权限列表: {permissions[:10]}...")  # 只打印前10个
        else:
            result.add_fail("用户信息API", f"status={resp.status_code}")
    except Exception as e:
        result.add_fail("用户信息API", str(e))

def test_permission_check(result: TestResult):
    """测试2: 权限检查API"""
    print("\n" + "="*50)
    print("测试2: 权限检查API")
    print("="*50)

    # 测试关键权限
    test_permissions = [
        ("platform:admin", True),
        ("platform:config", True),
        ("platform:deploy", True),
        ("node:start", True),
        ("node:stop", True),
        ("node:monitor", True),
        ("node:config", True),
        ("agent:register", True),
        ("agent:unregister", True),
        ("agent:manage", True),
        ("agent:service", True),
        ("wallet:create", True),
        ("wallet:bind", True),
        ("blockchain:stake", True),
        ("blockchain:vote", True),
        ("blockchain:govern", True),
        ("data:query", True),
        ("data:write", True),
        ("data:admin", True),
        ("chat:basic", True),
        ("chat:admin", True),
        ("system:health", True),
        ("system:metrics", True),
        ("system:logs", True),
        ("workspace", True),
        ("sandbox", True),
        ("browser", True),
        ("network", True),
        ("npm:public", True),
        ("npm:install", True),
        ("npm:run", True),
        ("npm:global", True),
        ("npm:danger", True),
        ("git:read", True),
        ("git:write", True),
        ("git:push", True),
        ("git:clone", True),
        ("git:force", True),
        ("git:danger", True),
    ]

    passed_count = 0
    for perm, expected in test_permissions:
        try:
            resp = requests.get(
                f"{BASE_URL}/api/meta-agent/permission/check-tool/{SUPERADMIN_WALLET}/{perm}",
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                has_permission = data.get("has_permission", False)
                if has_permission == expected:
                    passed_count += 1
                else:
                    result.add_fail(f"权限检查 {perm}", f"expected={expected}, got={has_permission}")
            else:
                result.add_fail(f"权限检查 {perm}", f"status={resp.status_code}")
        except Exception as e:
            result.add_fail(f"权限检查 {perm}", str(e))

    if passed_count >= 37:
        result.add_pass("权限检查完成", f"{passed_count}/37项通过")
    print(f"  通过: {passed_count}/{len(test_permissions)}")

def test_permission_stats(result: TestResult):
    """测试3: 权限统计API"""
    print("\n" + "="*50)
    print("测试3: 权限统计API")
    print("="*50)

    try:
        resp = requests.get(f"{BASE_URL}/api/meta-agent/permission/stats", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print(f"  统计数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
            result.add_pass("权限统计API")
        else:
            result.add_fail("权限统计API", f"status={resp.status_code}")
    except Exception as e:
        result.add_fail("权限统计API", str(e))

def test_tools_endpoint(result: TestResult):
    """测试4: 工具列表API"""
    print("\n" + "="*50)
    print("测试4: 工具列表API")
    print("="*50)

    try:
        resp = requests.get(f"{BASE_URL}/api/meta-agent/tools", timeout=10)
        if resp.status_code == 200:
            tools = resp.json()
            tool_count = len(tools.get("tools", []))
            print(f"  可用工具数量: {tool_count}")
            result.add_pass("工具列表API", f"{tool_count}个工具")
        else:
            result.add_fail("工具列表API", f"status={resp.status_code}")
    except Exception as e:
        result.add_fail("工具列表API", str(e))

def test_chat_endpoint(result: TestResult):
    """测试5: 对话API (chat:basic)"""
    print("\n" + "="*50)
    print("测试5: 对话API (chat:basic)")
    print("="*50)

    try:
        resp = requests.post(
            f"{BASE_URL}/api/meta-agent/chat",
            json={
                "wallet_address": SUPERADMIN_WALLET,
                "message": "你好，测试超级管理员对话功能",
                "context": {}
            },
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            response = data.get("response", "")[:100]
            print(f"  响应: {response}...")
            result.add_pass("对话API")
        else:
            result.add_fail("对话API", f"status={resp.status_code}, {resp.text[:100]}")
    except Exception as e:
        result.add_fail("对话API", str(e))

def test_health_endpoint(result: TestResult):
    """测试6: 健康检查API (system:health)"""
    print("\n" + "="*50)
    print("测试6: 健康检查API (system:health)")
    print("="*50)

    try:
        resp = requests.get(f"{BASE_URL}/api/health", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print(f"  健康状态: {data}")
            result.add_pass("健康检查API")
        else:
            result.add_fail("健康检查API", f"status={resp.status_code}")
    except Exception as e:
        result.add_fail("健康检查API", str(e))

def test_history_endpoint(result: TestResult):
    """测试7: 历史记录API (chat:admin)"""
    print("\n" + "="*50)
    print("测试7: 历史记录API (chat:admin)")
    print("="*50)

    try:
        resp = requests.get(
            f"{BASE_URL}/api/meta-agent/history/{SUPERADMIN_WALLET}",
            timeout=10
        )
        if resp.status_code == 200:
            history = resp.json()
            print(f"  历史记录数量: {len(history)}")
            result.add_pass("历史记录API")
        else:
            result.add_fail("历史记录API", f"status={resp.status_code}")
    except Exception as e:
        result.add_fail("历史记录API", str(e))

def test_human_permission(result: TestResult):
    """测试8: 对比human角色权限 (验证权限隔离)"""
    print("\n" + "="*50)
    print("测试8: 对比human角色权限 (验证权限隔离)")
    print("="*50)

    try:
        resp = requests.get(f"{BASE_URL}/api/meta-agent/user/{TEST_WALLET_HUMAN}", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            role = data.get("role")
            permissions = data.get("permissions", [])
            perm_count = len(permissions)

            print(f"  human角色: {role}")
            print(f"  human权限数量: {perm_count}")

            # human应该比superadmin少
            if perm_count < 37:
                result.add_pass("权限隔离验证", f"human({perm_count}) < superadmin(37)")
            else:
                result.add_fail("权限隔离验证", f"human权限不应等于superadmin")

            # 验证superadmin特有权限
            if "platform:admin" in permissions:
                result.add_fail("human不应有platform:admin", "")
            else:
                result.add_pass("human无platform:admin", "权限隔离正确")
        else:
            result.add_fail("human用户信息", f"status={resp.status_code}")
    except Exception as e:
        result.add_fail("human用户信息", str(e))

def test_check_tool_permission(result: TestResult):
    """测试9: 使用check-tool API验证具体工具权限"""
    print("\n" + "="*50)
    print("测试9: check-tool API验证具体工具权限")
    print("="*50)

    # 测试一些关键工具
    test_tools = [
        ("general_response", "chat:basic"),
        ("read_file", "workspace"),
        ("execute_python", "sandbox"),
        ("health_check", "system:health"),
        ("register_agent", "agent:register"),
        ("create_wallet", "wallet:create"),
    ]

    for tool_name, expected_perm in test_tools:
        try:
            resp = requests.get(
                f"{BASE_URL}/api/meta-agent/permission/check-tool/{SUPERADMIN_WALLET}/{expected_perm}",
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                has_perm = data.get("has_permission", False)
                if has_perm:
                    result.add_pass(f"工具 {tool_name}", f"权限={expected_perm}")
                else:
                    result.add_fail(f"工具 {tool_name}", f"缺少权限={expected_perm}")
            else:
                result.add_fail(f"工具 {tool_name}", f"API status={resp.status_code}")
        except Exception as e:
            result.add_fail(f"工具 {tool_name}", str(e))

def main():
    print("\n" + "="*60)
    print("超级管理员 (superadmin) 权限测试")
    print("="*60)
    print(f"测试用户: {SUPERADMIN_WALLET}")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    result = TestResult()

    # 执行所有测试
    test_user_info(result)
    test_permission_check(result)
    test_permission_stats(result)
    test_tools_endpoint(result)
    test_chat_endpoint(result)
    test_health_endpoint(result)
    test_history_endpoint(result)
    test_human_permission(result)
    test_check_tool_permission(result)

    # 输出结果汇总
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

    # 保存测试报告
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

    # 返回退出码
    sys.exit(0 if result.failed == 0 else 1)

if __name__ == "__main__":
    main()
