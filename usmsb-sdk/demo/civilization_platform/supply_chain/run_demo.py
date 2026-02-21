#!/usr/bin/env python3
"""
Supply Chain Demo - Main Program

启动所有 Agent 并演示完整的供应链报价流程。
支持 SDK HTTP Server 和 P2P 通信。

特性:
- 平台注册: Agent 启动时自动注册到新文明平台
- P2P 通信: Agent 之间可直接通信，无需中心化消息总线
- HTTP API: 每个 Agent 提供 REST API 接口

启动方式:
    # 自动模式 (运行所有场景)
    python run_demo.py

    # 交互式模式
    python run_demo.py -m interactive

    # 仅 HTTP 模式 (禁用 P2P)
    python run_demo.py --no-p2p

    # 指定平台 URL
    python run_demo.py --platform-url http://localhost:8000
"""

import asyncio
import argparse
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class AgentProcess:
    """Agent 进程管理器"""

    def __init__(
        self,
        agent_class,
        config_path: str,
        http_port: int,
        p2p_port: int,
        platform_url: str,
        enable_p2p: bool = True,
        bootstrap_peers: List = None,
        agent_id: str = None,
        agent_name: str = None,
    ):
        self.agent_class = agent_class
        self.config_path = config_path
        self.http_port = http_port
        self.p2p_port = p2p_port
        self.platform_url = platform_url
        self.enable_p2p = enable_p2p
        self.bootstrap_peers = bootstrap_peers or []
        self.custom_agent_id = agent_id
        self.custom_agent_name = agent_name

        self.agent = None
        self.task = None

    async def start(self) -> bool:
        """启动 Agent"""
        try:
            # 创建 Agent 实例
            self.agent = self.agent_class(config_path=self.config_path)

            # 覆盖 Agent ID 和名称（如果指定）
            if self.custom_agent_id:
                self.agent.agent_id = self.custom_agent_id
            if self.custom_agent_name:
                self.agent.name = self.custom_agent_name

            # 启动 Agent
            if self.enable_p2p:
                await self.agent.start_with_both(
                    http_port=self.http_port,
                    p2p_port=self.p2p_port,
                    platform_url=self.platform_url,
                    bootstrap_peers=self.bootstrap_peers,
                )
            else:
                await self.agent.start_with_http(
                    port=self.http_port,
                    platform_url=self.platform_url,
                )

            logger.info(
                f"Agent {self.agent.name} started: "
                f"HTTP={self.http_port}, P2P={self.p2p_port if self.enable_p2p else 'disabled'}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to start agent: {e}")
            return False

    async def stop(self) -> None:
        """停止 Agent"""
        if self.agent:
            await self.agent.stop()
            logger.info(f"Agent {self.agent.name} stopped")


class SupplyChainDemo:
    """供应链报价 Demo 主程序"""

    def __init__(
        self,
        config_dir: str = None,
        log_level: str = "INFO",
        enable_p2p: bool = True,
        platform_url: str = "http://localhost:8000",
    ):
        self.config_dir = config_dir or str(project_root)
        self.log_level = log_level
        self.enable_p2p = enable_p2p
        self.platform_url = platform_url

        # Agent 进程管理器
        self.agents: Dict[str, AgentProcess] = {}

        # 运行状态
        self.running = False

        # 交互日志
        self.interaction_log: List[Dict[str, Any]] = []

    async def start(self) -> None:
        """启动 Demo"""
        logger.info("=" * 60)
        logger.info("Supply Chain Quote Demo Starting...")
        logger.info(f"  Platform URL: {self.platform_url}")
        logger.info(f"  P2P Mode: {'enabled' if self.enable_p2p else 'disabled'}")
        logger.info("=" * 60)

        # 设置日志级别
        logging.getLogger().setLevel(getattr(logging, self.log_level.upper()))

        # 创建并启动所有 Agent
        await self._create_and_start_agents()

        self.running = True

        logger.info("=" * 60)
        logger.info("All agents started successfully!")
        logger.info("=" * 60)

        # 打印 Agent 信息
        self._print_agent_info()

    async def _create_and_start_agents(self) -> None:
        """创建并启动所有 Agent"""
        logger.info("Creating and starting agents...")

        # 导入 Agent 类
        from supplier_agent.agent import SupplierAgent
        from buyer_agent.agent import BuyerAgent
        from predictor_agent.agent import PredictorAgent
        from match_agent.agent import MatchAgent

        # Agent 配置
        agent_configs = [
            {
                "name": "supplier",
                "class": SupplierAgent,
                "config": os.path.join(self.config_dir, "supplier_agent", "config.yaml"),
                "http_port": 5101,
                "p2p_port": 9101,
            },
            {
                "name": "buyer",
                "class": BuyerAgent,
                "config": os.path.join(self.config_dir, "buyer_agent", "config.yaml"),
                "http_port": 5102,
                "p2p_port": 9102,
            },
            {
                "name": "predictor",
                "class": PredictorAgent,
                "config": os.path.join(self.config_dir, "predictor_agent", "config.yaml"),
                "http_port": 5103,
                "p2p_port": 9103,
            },
            {
                "name": "match",
                "class": MatchAgent,
                "config": os.path.join(self.config_dir, "match_agent", "config.yaml"),
                "http_port": 5104,
                "p2p_port": 9004,
            },
        ]

        # 收集所有 Agent 的 P2P 端口作为引导节点
        bootstrap_peers = []
        if self.enable_p2p:
            for cfg in agent_configs[:-1]:  # 除了最后一个
                bootstrap_peers.append(("127.0.0.1", cfg["p2p_port"]))

        # 按顺序启动 Agent
        for cfg in agent_configs:
            agent_process = AgentProcess(
                agent_class=cfg["class"],
                config_path=cfg["config"],
                http_port=cfg["http_port"],
                p2p_port=cfg["p2p_port"],
                platform_url=self.platform_url,
                enable_p2p=self.enable_p2p,
                bootstrap_peers=bootstrap_peers if self.enable_p2p else [],
            )

            success = await agent_process.start()
            if success:
                self.agents[cfg["name"]] = agent_process

            await asyncio.sleep(0.5)

        logger.info(f"All {len(self.agents)} agents started")

    def _print_agent_info(self) -> None:
        """打印 Agent 信息"""
        logger.info("\nAgent Endpoints:")
        logger.info("-" * 50)

        for name, agent_process in self.agents.items():
            agent = agent_process.agent
            logger.info(f"  {agent.name}:")
            logger.info(f"    HTTP: http://localhost:{agent_process.http_port}")
            logger.info(f"    Health: http://localhost:{agent_process.http_port}/health")
            logger.info(f"    Invoke: http://localhost:{agent_process.http_port}/invoke")
            if self.enable_p2p and hasattr(agent, "_p2p_server") and agent._p2p_server:
                logger.info(f"    P2P Port: {agent_process.p2p_port}")
                logger.info(f"    Peer ID: {agent._p2p_server.peer_id[:16]}...")

        logger.info("-" * 50)

    async def stop(self) -> None:
        """停止 Demo"""
        logger.info("Stopping Supply Chain Demo...")

        self.running = False

        # 停止所有 Agent
        for name, agent_process in self.agents.items():
            await agent_process.stop()

        self.agents.clear()

        logger.info("Demo stopped")

    def _log_interaction(self, event: str, details: Dict[str, Any]) -> None:
        """记录交互日志"""
        entry = {"timestamp": datetime.utcnow().isoformat(), "event": event, **details}
        self.interaction_log.append(entry)
        logger.info(f"[INTERACTION] {event}: {details}")

    async def run_scenario_simple_quote(self) -> Dict[str, Any]:
        """
        场景1: 简单询价报价

        Buyer 发起询价 -> Supplier 提供报价
        """
        logger.info("\n" + "=" * 60)
        logger.info("Scenario 1: Simple Quote Request")
        logger.info("=" * 60)

        self._log_interaction("scenario_start", {"scenario": "simple_quote"})

        buyer = self.agents.get("buyer")
        supplier = self.agents.get("supplier")

        if not buyer or not supplier:
            return {"error": "Agents not available"}

        # 1. Buyer 创建询价请求
        request = buyer.agent.create_quote_request(
            product_id="steel_001",
            product_name="钢板 Q235",
            quantity=100,
            unit="吨",
            delivery_date=(datetime.utcnow() + timedelta(days=14)).isoformat(),
            delivery_location="上海仓库",
            requirements={"target_price": 4500.0},
        )

        self._log_interaction(
            "quote_request_created",
            {
                "request_id": request["request_id"],
                "product": request["product_name"],
                "quantity": request["quantity"],
            },
        )

        # 2. Buyer 发送询价请求
        await buyer.agent.send_quote_request(request)

        # 等待报价响应
        await asyncio.sleep(2)

        # 3. 检查报价
        comparisons = buyer.agent.compare_quotes(request["request_id"])

        result = {
            "scenario": "simple_quote",
            "request_id": request["request_id"],
            "quotes_received": len(comparisons),
            "best_quote": comparisons[0] if comparisons else None,
        }

        self._log_interaction("scenario_complete", result)

        return result

    async def run_scenario_multi_supplier(self) -> Dict[str, Any]:
        """
        场景2: 多供应商竞争

        模拟多个供应商对同一询价提供不同报价
        """
        logger.info("\n" + "=" * 60)
        logger.info("Scenario 2: Multi-Supplier Competition")
        logger.info("=" * 60)

        self._log_interaction("scenario_start", {"scenario": "multi_supplier"})

        # 导入 SupplierAgent
        from supplier_agent.agent import SupplierAgent

        # 创建第二个供应商
        supplier2 = AgentProcess(
            agent_class=SupplierAgent,
            config_path=os.path.join(self.config_dir, "supplier_agent", "config.yaml"),
            http_port=5011,
            p2p_port=9011,
            platform_url=self.platform_url,
            enable_p2p=self.enable_p2p,
            agent_id="supplier_002",
            agent_name="第二钢材供应商",
        )

        # 启动第二个供应商
        await supplier2.start()

        # 修改基础价格以模拟竞争
        for product_id in supplier2.agent.inventory:
            supplier2.agent.inventory[product_id].base_price *= 0.95  # 便宜5%

        self._log_interaction(
            "supplier_joined",
            {"supplier_id": supplier2.agent.agent_id, "supplier_name": supplier2.agent.agent_name},
        )

        buyer = self.agents.get("buyer")

        # 发起询价
        request = buyer.agent.create_quote_request(
            product_id="steel_002",
            product_name="螺纹钢 HRB400",
            quantity=200,
            unit="吨",
            requirements={"target_price": 4200.0},
        )

        await buyer.agent.send_quote_request(request)

        # 等待所有报价
        await asyncio.sleep(2)

        # 比较报价
        comparisons = buyer.agent.compare_quotes(request["request_id"])

        result = {
            "scenario": "multi_supplier",
            "request_id": request["request_id"],
            "quotes_received": len(comparisons),
            "quotes": comparisons,
            "winner": comparisons[0] if comparisons else None,
        }

        self._log_interaction("scenario_complete", result)

        # 清理
        await supplier2.stop()

        return result

    async def run_scenario_price_prediction(self) -> Dict[str, Any]:
        """
        场景3: 价格预测辅助决策

        Predictor 提供价格预测，Buyer 根据预测决定采购时机
        """
        logger.info("\n" + "=" * 60)
        logger.info("Scenario 3: Price Prediction Assisted Decision")
        logger.info("=" * 60)

        self._log_interaction("scenario_start", {"scenario": "price_prediction"})

        buyer = self.agents.get("buyer")
        predictor = self.agents.get("predictor")

        if not buyer or not predictor:
            return {"error": "Agents not available"}

        # 1. 请求价格预测
        product_id = "steel_001"

        await buyer.agent.request_price_prediction(product_id, days_ahead=7)

        # 等待预测结果
        await asyncio.sleep(2)

        # 2. 检查预测结果
        prediction = buyer.agent.price_predictions.get(product_id)

        if prediction:
            self._log_interaction(
                "prediction_received",
                {
                    "product_id": product_id,
                    "trend": prediction.get("trend"),
                    "confidence": prediction.get("prediction_confidence"),
                    "recommendation": prediction.get("recommendation"),
                },
            )

        # 3. 根据预测决定是否采购
        should_buy = True
        if prediction and prediction.get("trend") == "down":
            should_buy = False
            self._log_interaction("decision", {"action": "wait", "reason": "Price trending down"})
        else:
            self._log_interaction("decision", {"action": "buy", "reason": "Good time to purchase"})

        result = {
            "scenario": "price_prediction",
            "product_id": product_id,
            "prediction": prediction,
            "decision": "buy" if should_buy else "wait",
        }

        self._log_interaction("scenario_complete", result)

        return result

    async def run_scenario_full_transaction(self) -> Dict[str, Any]:
        """
        场景4: 完整交易流程

        询价 -> 报价 -> 预测 -> 撮合 -> 确认 -> 完成
        """
        logger.info("\n" + "=" * 60)
        logger.info("Scenario 4: Full Transaction Flow")
        logger.info("=" * 60)

        self._log_interaction("scenario_start", {"scenario": "full_transaction"})

        buyer = self.agents.get("buyer")
        match = self.agents.get("match")

        if not buyer or not match:
            return {"error": "Agents not available"}

        # 1. 获取价格预测
        product_id = "steel_001"
        await buyer.agent.request_price_prediction(product_id)
        await asyncio.sleep(1)

        prediction = buyer.agent.price_predictions.get(product_id)
        self._log_interaction(
            "price_prediction_checked",
            {"trend": prediction.get("trend") if prediction else "unknown"},
        )

        # 2. 发起询价
        request = buyer.agent.create_quote_request(
            product_id="steel_001",
            product_name="钢板 Q235",
            quantity=150,
            unit="吨",
            delivery_date=(datetime.utcnow() + timedelta(days=10)).isoformat(),
            delivery_location="上海仓库",
            requirements={"target_price": 4500.0},
        )

        self._log_interaction(
            "quote_request_sent",
            {
                "request_id": request["request_id"],
                "product": request["product_name"],
                "quantity": request["quantity"],
            },
        )

        # 3. 广播询价请求
        await buyer.agent.broadcast(
            "quote_request",
            {
                **request,
                "buyer_id": buyer.agent.agent_id,
            },
        )

        # 等待供应商响应
        await asyncio.sleep(2)

        # 4. 检查收到的报价
        comparisons = buyer.agent.compare_quotes(request["request_id"])

        if comparisons:
            self._log_interaction(
                "quotes_received",
                {"count": len(comparisons), "best_price": comparisons[0].get("unit_price")},
            )

        # 5. 发送报价响应给 MatchAgent（触发撮合）
        if comparisons:
            best_quote = comparisons[0]
            await match.agent.handle_quote_response(
                {"payload": best_quote, "sender_id": best_quote.get("supplier_id")}
            )

            await asyncio.sleep(2)

        # 6. 检查撮合结果
        stats = match.agent.get_stats()
        self._log_interaction(
            "matching_complete",
            {
                "completed_matches": stats.get("completed_matches", 0),
                "pending_matches": stats.get("pending_matches", 0),
            },
        )

        result = {
            "scenario": "full_transaction",
            "request_id": request["request_id"],
            "quotes_received": len(comparisons),
            "match_stats": stats,
            "completed": stats.get("completed_matches", 0) > 0,
        }

        self._log_interaction("scenario_complete", result)

        return result

    async def run_all_scenarios(self) -> Dict[str, Any]:
        """运行所有场景"""
        results = {}

        try:
            results["scenario_1"] = await self.run_scenario_simple_quote()
            await asyncio.sleep(1)

            results["scenario_2"] = await self.run_scenario_multi_supplier()
            await asyncio.sleep(1)

            results["scenario_3"] = await self.run_scenario_price_prediction()
            await asyncio.sleep(1)

            results["scenario_4"] = await self.run_scenario_full_transaction()

        except Exception as e:
            logger.error(f"Error running scenarios: {e}")
            results["error"] = str(e)

        return results

    async def run_interactive(self) -> None:
        """交互式模式 - 默认 keep"""
        logger.info("\nStarting interactive mode (auto-keep enabled)...")
        logger.info("Agents are running. Press Ctrl+C to stop...")

        while self.running:
            await asyncio.sleep(1)

    def _print_stats(self) -> None:
        """打印 Agent 统计信息"""
        logger.info("\n--- Agent Statistics ---")

        for name, agent_process in self.agents.items():
            if agent_process.agent:
                stats = agent_process.agent.get_stats()
                logger.info(f"{agent_process.agent.name}: {stats}")

    def _print_history(self) -> None:
        """打印交互历史"""
        logger.info("\n--- Interaction History ---")

        for entry in self.interaction_log[-20:]:  # 最近20条
            timestamp = entry.get("timestamp", "")
            event = entry.get("event", "")
            logger.info(f"[{timestamp}] {event}")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Supply Chain Quote Demo")
    parser.add_argument(
        "--mode",
        "-m",
        choices=["auto", "interactive"],
        default="auto",
        help="Demo mode (auto or interactive)",
    )
    parser.add_argument(
        "--scenario",
        "-s",
        choices=["1", "2", "3", "4", "all"],
        default="all",
        help="Scenario to run (1-4 or all)",
    )
    parser.add_argument(
        "--log-level",
        "-l",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level",
    )
    parser.add_argument("--config-dir", "-c", default=None, help="Configuration directory")
    parser.add_argument(
        "--platform-url",
        default="http://localhost:8000",
        help="Platform URL for agent registration",
    )
    parser.add_argument("--no-p2p", action="store_true", help="Disable P2P mode (HTTP only)")

    args = parser.parse_args()

    demo = SupplyChainDemo(
        config_dir=args.config_dir,
        log_level=args.log_level,
        enable_p2p=not args.no_p2p,
        platform_url=args.platform_url,
    )

    try:
        await demo.start()

        if args.mode == "interactive":
            # 交互模式默认输入 keep 让 agents 保持运行
            await demo.run_interactive()
        else:
            # 自动模式
            if args.scenario == "1":
                await demo.run_scenario_simple_quote()
            elif args.scenario == "2":
                await demo.run_scenario_multi_supplier()
            elif args.scenario == "3":
                await demo.run_scenario_price_prediction()
            elif args.scenario == "4":
                await demo.run_scenario_full_transaction()
            else:
                await demo.run_all_scenarios()

            # 打印最终统计
            demo._print_stats()

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Demo error: {e}", exc_info=True)
    finally:
        await demo.stop()

    logger.info("Demo finished")


if __name__ == "__main__":
    asyncio.run(main())
