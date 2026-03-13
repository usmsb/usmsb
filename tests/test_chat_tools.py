"""
测试 Meta Agent Chat 接口的工具调用

通过 chat 接口测试所有工具是否正常工作
钱包地址: 0x382B71e8b425CFAaD1B1C6D970481F440458Abf8

运行方式:
    cd usmsb-sdk
    python tests/test_chat_tools.py
"""

import asyncio
import httpx
import json
import sys
from typing import Dict, List, Optional
from datetime import datetime

# 配置
BASE_URL = "http://127.0.0.1:8001"
WALLET_ADDRESS = "0x382B71e8b425CFAaD1B1C6D970481F440458Abf8"

# 测试用例定义
TEST_CASES = [
    # 基础工具测试
    {
        "name": "health_check",
        "message": "请检查系统健康状态",
        "expected_tool": "health_check",
        "category": "基础工具",
    },
    {
        "name": "get_metrics",
        "message": "获取系统指标",
        "expected_tool": "get_metrics",
        "category": "基础工具",
    },
    {
        "name": "start_node",
        "message": "启动节点 node_1",
        "expected_tool": "start_node",
        "category": "平台工具",
    },
    {
        "name": "get_node_status",
        "message": "获取节点 node_1 的状态",
        "expected_tool": "get_node_status",
        "category": "平台工具",
    },
    # 区块链工具测试
    {
        "name": "get_balance",
        "message": "查询我的余额",
        "expected_tool": "get_balance",
        "category": "区块链工具",
    },
    {
        "name": "get_chain_info",
        "message": "获取以太坊链信息",
        "expected_tool": "get_chain_info",
        "category": "区块链工具",
    },
    # 数据库工具测试
    {
        "name": "query_db",
        "message": "查询数据库中的用户表",
        "expected_tool": "query_db",
        "category": "数据库工具",
    },
    # 监控工具测试
    {
        "name": "get_alerts",
        "message": "获取告警列表",
        "expected_tool": "get_alerts",
        "category": "监控工具",
    },
    # 需要文件系统的工具测试
    {
        "name": "list_directory",
        "message": "列出我的工作空间根目录",
        "expected_tool": "list_directory",
        "category": "文件系统工具",
        "requires_session": True,
    },
    {
        "name": "write_file",
        "message": "创建一个测试文件 test.txt，内容是 'Hello World'",
        "expected_tool": "write_file",
        "category": "文件系统工具",
        "requires_session": True,
    },
    {
        "name": "read_file",
        "message": "读取测试文件 test.txt",
        "expected_tool": "read_file",
        "category": "文件系统工具",
        "requires_session": True,
    },
    # 代码执行测试
    {
        "name": "execute_python",
        "message": "执行 Python 代码: print('Hello from sandbox')",
        "expected_tool": "execute_python",
        "category": "代码执行",
        "requires_session": True,
    },
    # Web 工具测试
    {
        "name": "fetch_url",
        "message": "获取网页 https://httpbin.org/get 的内容",
        "expected_tool": "fetch_url",
        "category": "Web工具",
    },
]


class ChatToolTester:
    """Chat 接口工具测试器"""

    def __init__(self, base_url: str, wallet_address: str):
        self.base_url = base_url
        self.wallet_address = wallet_address
        self.results: List[Dict] = []
        self.client = httpx.AsyncClient(timeout=60.0)

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()

    async def send_chat(self, message: str) -> Dict:
        """发送 chat 请求"""
        url = f"{self.base_url}/meta-agent/chat"
        payload = {
            "message": message,
            "wallet_address": self.wallet_address,
        }

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            return {"error": str(e), "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}

    async def get_tools(self) -> List[Dict]:
        """获取可用工具列表"""
        url = f"{self.base_url}/meta-agent/tools"
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"获取工具列表失败: {e}")
            return []

    async def run_test(self, test_case: Dict) -> Dict:
        """运行单个测试"""
        print(f"\n{'='*60}")
        print(f"测试: {test_case['name']}")
        print(f"类别: {test_case['category']}")
        print(f"消息: {test_case['message']}")
        print(f"{'='*60}")

        result = {
            "name": test_case["name"],
            "category": test_case["category"],
            "message": test_case["message"],
            "expected_tool": test_case["expected_tool"],
            "requires_session": test_case.get("requires_session", False),
            "timestamp": datetime.now().isoformat(),
            "status": "pending",
            "response": None,
            "error": None,
        }

        try:
            response = await self.send_chat(test_case["message"])
            result["response"] = response

            if "error" in response:
                result["status"] = "error"
                result["error"] = response["error"]
                print(f"❌ 错误: {response['error']}")
            elif response.get("success"):
                result["status"] = "success"
                print(f"✅ 成功")
                print(f"响应: {response.get('response', '')[:200]}...")
            else:
                result["status"] = "failed"
                result["error"] = response.get("response", "Unknown error")
                print(f"❌ 失败: {response.get('response', '')[:200]}")

        except Exception as e:
            result["status"] = "exception"
            result["error"] = str(e)
            print(f"❌ 异常: {e}")

        self.results.append(result)
        return result

    async def run_all_tests(self, test_cases: List[Dict]):
        """运行所有测试"""
        print(f"\n开始测试 Chat 接口工具调用")
        print(f"服务地址: {self.base_url}")
        print(f"钱包地址: {self.wallet_address}")
        print(f"测试数量: {len(test_cases)}")

        # 先获取工具列表
        print("\n获取可用工具列表...")
        tools = await self.get_tools()
        if tools:
            print(f"可用工具: {len(tools)} 个")
            for tool in tools[:10]:  # 只显示前10个
                print(f"  - {tool.get('name')}: {tool.get('description', '')[:50]}")
            if len(tools) > 10:
                print(f"  ... 还有 {len(tools) - 10} 个工具")

        # 按类别分组测试
        categories = {}
        for tc in test_cases:
            cat = tc["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(tc)

        # 逐类测试
        for category, tests in categories.items():
            print(f"\n\n{'#'*60}")
            print(f"# 测试类别: {category}")
            print(f"{'#'*60}")

            for tc in tests:
                await self.run_test(tc)
                # 稍微等待一下，避免请求过快
                await asyncio.sleep(1)

    def print_summary(self):
        """打印测试摘要"""
        print(f"\n\n{'='*60}")
        print("测试摘要")
        print(f"{'='*60}")

        total = len(self.results)
        success = sum(1 for r in self.results if r["status"] == "success")
        failed = sum(1 for r in self.results if r["status"] == "failed")
        error = sum(1 for r in self.results if r["status"] == "error")
        exception = sum(1 for r in self.results if r["status"] == "exception")

        print(f"总计: {total}")
        print(f"✅ 成功: {success}")
        print(f"❌ 失败: {failed}")
        print(f"⚠️ 错误: {error}")
        print(f"💥 异常: {exception}")

        # 按类别统计
        print(f"\n按类别统计:")
        categories = {}
        for r in self.results:
            cat = r["category"]
            if cat not in categories:
                categories[cat] = {"success": 0, "failed": 0, "total": 0}
            categories[cat]["total"] += 1
            if r["status"] == "success":
                categories[cat]["success"] += 1
            else:
                categories[cat]["failed"] += 1

        for cat, stats in categories.items():
            status = "✅" if stats["failed"] == 0 else "⚠️"
            print(
                f"  {status} {cat}: {stats['success']}/{stats['total']} 成功"
            )

        # 显示失败的测试
        failed_tests = [r for r in self.results if r["status"] != "success"]
        if failed_tests:
            print(f"\n失败的测试:")
            for r in failed_tests:
                print(f"  ❌ {r['name']}: {r['error'][:100] if r['error'] else 'Unknown'}")

        return {
            "total": total,
            "success": success,
            "failed": failed + error + exception,
        }


async def main():
    """主函数"""
    tester = ChatToolTester(BASE_URL, WALLET_ADDRESS)

    try:
        await tester.run_all_tests(TEST_CASES)
        summary = tester.print_summary()

        # 保存结果到文件
        result_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "summary": summary,
                    "results": tester.results,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        print(f"\n结果已保存到: {result_file}")

    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())
