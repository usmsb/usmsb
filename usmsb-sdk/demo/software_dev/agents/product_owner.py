"""
Product Owner Agent - 负责需求分析、任务拆分和验收
"""

from typing import Any, Dict, List, Optional
from demo.shared.base_demo_agent import DemoAgent, DemoMessage
from usmsb_sdk.agent_sdk import AgentConfig


class ProductOwnerAgent(DemoAgent):
    """
    产品经理 AI Agent

    职责：
    - 发布需求
    - 拆分任务
    - 验收功能
    - 协调团队
    """

    def __init__(self, config: AgentConfig, visualizer=None):
        super().__init__(config, scenario_name="software_dev", visualizer=visualizer)
        self.requirements: List[Dict] = []
        self.tasks: List[Dict] = []
        self.accepted_features: List[str] = []

    async def _setup_skills(self):
        """设置技能"""
        self.register_skill(
            name="analyze_requirement",
            description="分析需求并拆分为任务",
            handler=self._analyze_requirement,
            parameters={"requirement": "需求描述"}
        )

        self.register_skill(
            name="accept_feature",
            description="验收功能",
            handler=self._accept_feature,
            parameters={"feature_id": "功能ID", "test_results": "测试结果"}
        )

        self.register_skill(
            name="prioritize_tasks",
            description="任务优先级排序",
            handler=self._prioritize_tasks,
            parameters={"tasks": "任务列表"}
        )

    async def _setup_capabilities(self):
        """设置能力"""
        self.register_capability("requirement_analysis", "需求分析和拆分", 0.9)
        self.register_capability("prioritization", "优先级排序", 0.85)
        self.register_capability("acceptance_testing", "验收测试", 0.8)
        self.register_capability("team_coordination", "团队协调", 0.85)

    async def _analyze_requirement(self, params: Dict) -> Dict:
        """分析需求并拆分为任务"""
        requirement = params.get("requirement", "")

        # 模拟需求分析
        analysis = {
            "requirement": requirement,
            "user_stories": [
                {"id": f"US-{i+1}", "story": f"作为用户，我希望{requirement}的{i+1}部分"}
                for i in range(3)
            ],
            "tasks": [
                {"id": f"TASK-{i+1}", "title": f"实现{requirement}的任务{i+1}", "priority": 3-i}
                for i in range(3)
            ],
            "acceptance_criteria": [
                f"验收标准{i+1}: 功能正常工作"
                for i in range(3)
            ]
        }

        self.requirements.append(analysis)

        self._log_action("analyze_requirement", {
            "requirement": requirement[:50],
            "tasks_count": len(analysis["tasks"])
        })

        return analysis

    async def _accept_feature(self, params: Dict) -> Dict:
        """验收功能"""
        feature_id = params.get("feature_id", "")
        test_results = params.get("test_results", {})

        # 模拟验收决策
        passed = test_results.get("passed", True)

        result = {
            "feature_id": feature_id,
            "accepted": passed,
            "feedback": "功能符合预期，验收通过！" if passed else "存在问题，需要修改"
        }

        if passed:
            self.accepted_features.append(feature_id)

        self._log_action("accept_feature", {
            "feature_id": feature_id,
            "accepted": passed
        })

        return result

    async def _prioritize_tasks(self, params: Dict) -> Dict:
        """任务优先级排序"""
        tasks = params.get("tasks", [])

        # 按优先级排序
        sorted_tasks = sorted(tasks, key=lambda x: x.get("priority", 0), reverse=True)

        self.tasks = sorted_tasks

        self._log_action("prioritize_tasks", {
            "tasks_count": len(sorted_tasks)
        })

        return {"sorted_tasks": sorted_tasks}

    async def publish_requirement(self, requirement: str) -> DemoMessage:
        """发布需求给团队"""
        self.logger.info(f"📋 发布需求: {requirement}")

        # 分析需求
        analysis = await self._analyze_requirement({"requirement": requirement})

        # 广播给团队
        msg = await self.send_message(
            receiver="broadcast",
            content={
                "type": "new_requirement",
                "requirement": requirement,
                "analysis": analysis,
            },
            message_type="task"
        )

        return msg

    async def receive_delivery(self, delivery: Dict) -> Dict:
        """接收交付"""
        feature_id = delivery.get("feature_id", "")
        test_results = delivery.get("test_results", {})

        result = await self._accept_feature({
            "feature_id": feature_id,
            "test_results": test_results
        })

        return result


def create_product_owner() -> ProductOwnerAgent:
    """创建 Product Owner Agent"""
    config = AgentConfig(
        name="ProductOwner",
        description="产品经理 AI - 负责需求分析和任务拆分",
        capabilities=["requirement_analysis", "prioritization", "acceptance_testing"],
        endpoint="http://localhost:8001",
    )
    return ProductOwnerAgent(config)
