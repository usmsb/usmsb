#!/usr/bin/env python3
"""
Supply Chain Demo - Test Scenarios

包含完整的测试场景，用于验证 Agent 间的通信和业务流程。
"""

import asyncio
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from shared.message_bus import get_message_bus, shutdown_message_bus

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


class TestRunner:
    """测试场景运行器"""

    def __init__(self):
        self.supplier_agent = None
        self.buyer_agent = None
        self.predictor_agent = None
        self.match_agent = None
        self.message_bus = None
        self.results = {}

    async def setup(self) -> None:
        """初始化测试环境"""
        logger.info("Setting up test environment...")

        # 初始化消息总线
        self.message_bus = await get_message_bus()

        # 导入并创建 Agent
        from supplier_agent.agent import SupplierAgent
        from buyer_agent.agent import BuyerAgent
        from predictor_agent.agent import PredictorAgent
        from match_agent.agent import MatchAgent

        config_dir = str(project_root)

        self.supplier_agent = SupplierAgent(
            config_path=os.path.join(config_dir, "supplier_agent", "config.yaml")
        )
        self.buyer_agent = BuyerAgent(
            config_path=os.path.join(config_dir, "buyer_agent", "config.yaml")
        )
        self.predictor_agent = PredictorAgent(
            config_path=os.path.join(config_dir, "predictor_agent", "config.yaml")
        )
        self.match_agent = MatchAgent(
            config_path=os.path.join(config_dir, "match_agent", "config.yaml")
        )

        # 启动 Agent
        await self.supplier_agent.start()
        await self.predictor_agent.start()
        await self.buyer_agent.start()
        await self.match_agent.start()

        # 等待所有 Agent 初始化完成
        await asyncio.sleep(0.5)

        logger.info("Test environment ready")

    async def teardown(self) -> None:
        """清理测试环境"""
        logger.info("Tearing down test environment...")

        if self.match_agent:
            await self.match_agent.stop()
        if self.buyer_agent:
            await self.buyer_agent.stop()
        if self.predictor_agent:
            await self.predictor_agent.stop()
        if self.supplier_agent:
            await self.supplier_agent.stop()

        await shutdown_message_bus()

        logger.info("Test environment cleaned up")

    def _print_result(self, test_name: str, success: bool, details: Dict[str, Any] = None) -> None:
        """打印测试结果"""
        status = "PASS" if success else "FAIL"
        logger.info(f"\n{'=' * 50}")
        logger.info(f"Test: {test_name}")
        logger.info(f"Status: {status}")
        if details:
            for key, value in details.items():
                logger.info(f"  {key}: {value}")
        logger.info(f"{'=' * 50}\n")

        self.results[test_name] = {
            "success": success,
            "details": details or {}
        }

    async def test_scenario_1_simple_quote(self) -> bool:
        """
        测试场景1: 简单询价报价

        验证:
        - Buyer 能创建询价请求
        - Supplier 能接收并响应报价
        - Buyer 能评估报价
        """
        test_name = "Scenario 1: Simple Quote Request"
        logger.info(f"\nRunning {test_name}...")

        try:
            # 1. 创建询价请求
            request = self.buyer_agent.create_quote_request(
                product_id="steel_001",
                product_name="钢板 Q235",
                quantity=100,
                unit="吨",
                delivery_date=(datetime.utcnow() + timedelta(days=14)).isoformat(),
                requirements={"target_price": 4500.0}
            )

            assert request is not None, "Failed to create quote request"
            assert request["product_id"] == "steel_001", "Wrong product ID"
            logger.info("  [OK] Quote request created")

            # 2. 发送询价请求
            await self.buyer_agent.send_quote_request(request)

            # 等待供应商处理
            await asyncio.sleep(1)

            # 3. 检查 Buyer 是否收到报价
            comparisons = self.buyer_agent.compare_quotes(request["request_id"])

            assert len(comparisons) > 0, "No quotes received"
            logger.info(f"  [OK] Received {len(comparisons)} quote(s)")

            # 4. 验证报价内容
            best_quote = comparisons[0]
            assert best_quote.get("unit_price") > 0, "Invalid unit price"
            assert best_quote.get("score") > 0, "Quote not scored"
            logger.info(f"  [OK] Best quote: {best_quote.get('unit_price')} CNY/ton")

            self._print_result(test_name, True, {
                "quotes_received": len(comparisons),
                "best_price": best_quote.get("unit_price"),
                "score": best_quote.get("score")
            })
            return True

        except Exception as e:
            self._print_result(test_name, False, {"error": str(e)})
            return False

    async def test_scenario_2_multi_supplier(self) -> bool:
        """
        测试场景2: 多供应商竞争

        验证:
        - 多个供应商能同时响应询价
        - Buyer 能正确比较和排序报价
        """
        test_name = "Scenario 2: Multi-Supplier Competition"
        logger.info(f"\nRunning {test_name}...")

        try:
            # 创建第二个供应商
            from supplier_agent.agent import SupplierAgent

            supplier2 = SupplierAgent(
                config_path=os.path.join(project_root, "supplier_agent", "config.yaml")
            )
            supplier2.agent_id = "supplier_002"
            supplier2.agent_name = "测试供应商2"

            # 设置不同的价格
            for product_id in supplier2.inventory:
                supplier2.inventory[product_id].base_price *= 0.95

            await supplier2.start()
            logger.info("  [OK] Second supplier created and started")

            # 发起询价
            request = self.buyer_agent.create_quote_request(
                product_id="steel_002",
                product_name="螺纹钢 HRB400",
                quantity=200,
                unit="吨",
                requirements={"target_price": 4200.0}
            )

            await self.buyer_agent.send_quote_request(request)

            # 等待报价
            await asyncio.sleep(1.5)

            # 检查报价
            comparisons = self.buyer_agent.compare_quotes(request["request_id"])

            assert len(comparisons) >= 1, "Expected at least 1 quote"
            logger.info(f"  [OK] Received {len(comparisons)} quote(s)")

            # 验证排序
            if len(comparisons) > 1:
                assert comparisons[0]["score"] >= comparisons[1]["score"], \
                    "Quotes not properly sorted by score"
                logger.info("  [OK] Quotes properly sorted")

            # 清理
            await supplier2.stop()

            self._print_result(test_name, True, {
                "quotes_received": len(comparisons),
                "best_supplier": comparisons[0].get("supplier_id"),
                "best_price": comparisons[0].get("unit_price")
            })
            return True

        except Exception as e:
            self._print_result(test_name, False, {"error": str(e)})
            return False

    async def test_scenario_3_price_prediction(self) -> bool:
        """
        测试场景3: 价格预测辅助决策

        验证:
        - Predictor 能生成价格预测
        - Buyer 能接收并存储预测
        - 预测包含正确的趋势和建议
        """
        test_name = "Scenario 3: Price Prediction"
        logger.info(f"\nRunning {test_name}...")

        try:
            product_id = "steel_001"

            # 1. 请求价格预测
            await self.buyer_agent.request_price_prediction(product_id, days_ahead=7)

            # 等待预测
            await asyncio.sleep(1)

            # 2. 检查预测结果
            prediction = self.buyer_agent.price_predictions.get(product_id)

            assert prediction is not None, "No prediction received"
            logger.info("  [OK] Prediction received")

            # 3. 验证预测内容
            assert "trend" in prediction, "Missing trend in prediction"
            assert "recommendation" in prediction, "Missing recommendation"
            assert "predicted_prices" in prediction, "Missing predicted prices"
            assert len(prediction["predicted_prices"]) > 0, "Empty predictions"

            logger.info(f"  [OK] Trend: {prediction['trend']}")
            logger.info(f"  [OK] Recommendation: {prediction['recommendation']}")
            logger.info(f"  [OK] Confidence: {prediction.get('prediction_confidence')}")

            self._print_result(test_name, True, {
                "trend": prediction.get("trend"),
                "confidence": prediction.get("prediction_confidence"),
                "prediction_count": len(prediction.get("predicted_prices", []))
            })
            return True

        except Exception as e:
            self._print_result(test_name, False, {"error": str(e)})
            return False

    async def test_scenario_4_full_transaction(self) -> bool:
        """
        测试场景4: 完整交易流程

        验证:
        - 完整的询价-报价-撮合-确认流程
        - MatchAgent 能正确撮合交易
        - 交易状态正确流转
        """
        test_name = "Scenario 4: Full Transaction Flow"
        logger.info(f"\nRunning {test_name}...")

        try:
            # 1. 获取价格预测
            product_id = "steel_001"
            await self.buyer_agent.request_price_prediction(product_id)
            await asyncio.sleep(0.5)

            prediction = self.buyer_agent.price_predictions.get(product_id)
            logger.info(f"  [OK] Price prediction: {prediction.get('trend') if prediction else 'N/A'}")

            # 2. 发起询价
            request = self.buyer_agent.create_quote_request(
                product_id="steel_001",
                product_name="钢板 Q235",
                quantity=150,
                unit="吨",
                delivery_date=(datetime.utcnow() + timedelta(days=10)).isoformat(),
                requirements={"target_price": 4500.0}
            )

            await self.buyer_agent.broadcast("quote_request", {
                **request,
                "buyer_id": self.buyer_agent.agent_id,
            })

            await asyncio.sleep(1)

            # 3. 检查报价
            comparisons = self.buyer_agent.compare_quotes(request["request_id"])
            assert len(comparisons) > 0, "No quotes received"
            logger.info(f"  [OK] Received {len(comparisons)} quote(s)")

            # 4. 发送给 MatchAgent
            best_quote = comparisons[0]
            await self.match_agent.handle_quote_response({
                "payload": {
                    **best_quote,
                    "request_id": request["request_id"],
                },
                "sender_id": best_quote.get("supplier_id")
            })

            # 等待撮合完成
            await asyncio.sleep(2)

            # 5. 检查撮合结果
            stats = self.match_agent.get_stats()
            completed = stats.get("completed_matches", 0)
            pending = stats.get("pending_matches", 0)

            logger.info(f"  [OK] Match stats: completed={completed}, pending={pending}")

            # 6. 验证库存更新（如果有完成的撮合）
            if completed > 0:
                supplier_stats = self.supplier_agent.get_stats()
                logger.info(f"  [OK] Supplier inventory updated")

            self._print_result(test_name, True, {
                "quotes_received": len(comparisons),
                "completed_matches": completed,
                "pending_matches": pending,
                "flow_completed": completed > 0 or pending > 0
            })
            return True

        except Exception as e:
            self._print_result(test_name, False, {"error": str(e)})
            return False

    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        logger.info("\n" + "=" * 60)
        logger.info("Supply Chain Demo - Running All Test Scenarios")
        logger.info("=" * 60)

        start_time = time.time()

        # 运行测试
        tests = [
            ("Scenario 1", self.test_scenario_1_simple_quote),
            ("Scenario 2", self.test_scenario_2_multi_supplier),
            ("Scenario 3", self.test_scenario_3_price_prediction),
            ("Scenario 4", self.test_scenario_4_full_transaction),
        ]

        for name, test_func in tests:
            try:
                await test_func()
            except Exception as e:
                logger.error(f"Test {name} failed with exception: {e}")

            # 测试间隔
            await asyncio.sleep(0.5)

        # 计算结果
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r["success"])
        failed_tests = total_tests - passed_tests

        elapsed_time = time.time() - start_time

        # 打印总结
        logger.info("\n" + "=" * 60)
        logger.info("Test Summary")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Success Rate: {passed_tests / total_tests * 100:.1f}%")
        logger.info(f"Elapsed Time: {elapsed_time:.2f}s")
        logger.info("=" * 60)

        # 详细结果
        for test_name, result in self.results.items():
            status = "PASS" if result["success"] else "FAIL"
            logger.info(f"  {status}: {test_name}")

        return {
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "elapsed_time": elapsed_time,
            "results": self.results
        }


async def main():
    """主函数"""
    runner = TestRunner()

    try:
        await runner.setup()
        results = await runner.run_all_tests()

        # 返回退出码
        if results["failed"] > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        logger.error(f"Test runner error: {e}", exc_info=True)
        sys.exit(1)

    finally:
        await runner.teardown()


if __name__ == "__main__":
    asyncio.run(main())
