"""
Architect Agent - 负责技术设计、架构决策
"""

from typing import Any, Dict, List, Optional
from demo.shared.base_demo_agent import DemoAgent
from usmsb_sdk.agent_sdk import AgentConfig


class ArchitectAgent(DemoAgent):
    """
    架构师 AI Agent

    职责：
    - 技术架构设计
    - 技术选型
    - 任务技术拆分
    - 设计文档输出
    """

    def __init__(self, config: AgentConfig, visualizer=None):
        super().__init__(config, scenario_name="software_dev", visualizer=visualizer)
        self.designs: List[Dict] = []
        self.tech_stack: Dict = {}

    async def _setup_skills(self):
        """设置技能"""
        self.register_skill(
            name="design_architecture",
            description="设计系统架构",
            handler=self._design_architecture,
            parameters={"requirement": "需求描述"}
        )

        self.register_skill(
            name="select_tech_stack",
            description="技术选型",
            handler=self._select_tech_stack,
            parameters={"requirements": "技术要求"}
        )

        self.register_skill(
            name="create_technical_tasks",
            description="创建技术任务",
            handler=self._create_technical_tasks,
            parameters={"design": "设计方案"}
        )

    async def _setup_capabilities(self):
        """设置能力"""
        self.register_capability("architecture_design", "架构设计", 0.95)
        self.register_capability("tech_selection", "技术选型", 0.9)
        self.register_capability("api_design", "API 设计", 0.9)
        self.register_capability("database_design", "数据库设计", 0.85)

    async def _design_architecture(self, params: Dict) -> Dict:
        """设计系统架构"""
        requirement = params.get("requirement", "")

        # 模拟架构设计
        design = {
            "requirement": requirement,
            "architecture": {
                "frontend": {"framework": "React", "state": "Redux"},
                "backend": {"framework": "FastAPI", "language": "Python"},
                "database": {"type": "PostgreSQL", "cache": "Redis"},
                "messaging": {"type": "WebSocket", "broker": "RabbitMQ"},
            },
            "modules": [
                {"name": "AuthModule", "description": "认证授权模块"},
                {"name": "CoreModule", "description": "核心业务模块"},
                {"name": "ApiModule", "description": "API 网关模块"},
            ],
            "api_endpoints": [
                {"path": "/api/auth/login", "method": "POST", "description": "用户登录"},
                {"path": "/api/auth/register", "method": "POST", "description": "用户注册"},
                {"path": "/api/users/profile", "method": "GET", "description": "用户信息"},
            ],
            "data_models": [
                {"name": "User", "fields": ["id", "username", "email", "password_hash"]},
                {"name": "Session", "fields": ["id", "user_id", "token", "expires_at"]},
            ],
        }

        self.designs.append(design)

        self._log_action("design_architecture", {
            "requirement": requirement[:50],
            "modules_count": len(design["modules"])
        })

        return design

    async def _select_tech_stack(self, params: Dict) -> Dict:
        """技术选型"""
        requirements = params.get("requirements", "")

        # 模拟技术选型决策
        tech_stack = {
            "language": "Python 3.12",
            "framework": "FastAPI",
            "database": "PostgreSQL 16",
            "cache": "Redis 7",
            "message_queue": "RabbitMQ",
            "container": "Docker",
            "orchestration": "Kubernetes",
            "monitoring": "Prometheus + Grafana",
            "logging": "ELK Stack",
            "ci_cd": "GitHub Actions",
        }

        self.tech_stack = tech_stack

        self._log_action("select_tech_stack", {
            "tech_count": len(tech_stack)
        })

        return tech_stack

    async def _create_technical_tasks(self, params: Dict) -> Dict:
        """创建技术任务"""
        design = params.get("design", {})

        # 基于设计创建技术任务
        tasks = []

        for module in design.get("modules", []):
            tasks.append({
                "id": f"TECH-{module['name']}-001",
                "module": module["name"],
                "title": f"实现 {module['name']}",
                "description": module["description"],
                "assignee": "Developer",
                "priority": "high",
                "estimated_hours": 8,
            })

        for endpoint in design.get("api_endpoints", []):
            tasks.append({
                "id": f"API-{endpoint['path'].replace('/', '-')}",
                "type": "api",
                "title": f"实现 {endpoint['method']} {endpoint['path']}",
                "description": endpoint["description"],
                "assignee": "Developer",
                "priority": "medium",
                "estimated_hours": 2,
            })

        self._log_action("create_technical_tasks", {
            "tasks_count": len(tasks)
        })

        return {"tasks": tasks}

    async def handle_message(self, message: Any, session=None) -> Any:
        """处理消息"""
        msg = self._wrap_message(message)
        content = self._extract_content(message)

        # 如果收到需求，进行架构设计
        if isinstance(content, dict) and content.get("type") == "new_requirement":
            requirement = content.get("requirement", "")

            # 设计架构
            design = await self._design_architecture({"requirement": requirement})

            # 选择技术栈
            tech_stack = await self._select_tech_stack({"requirements": requirement})

            # 创建技术任务
            tasks_result = await self._create_technical_tasks({"design": design})

            # 发送给 Developer
            response = await self.send_message(
                receiver="Developer",
                content={
                    "type": "technical_design",
                    "design": design,
                    "tech_stack": tech_stack,
                    "tasks": tasks_result["tasks"],
                },
                message_type="task"
            )

            return {"status": "design_completed", "tasks_created": len(tasks_result["tasks"])}

        return await super().handle_message(message, session)


def create_architect() -> ArchitectAgent:
    """创建 Architect Agent"""
    config = AgentConfig(
        name="Architect",
        description="架构师 AI - 负责技术设计和架构决策",
        capabilities=["architecture_design", "tech_selection", "api_design", "database_design"],
        endpoint="http://localhost:8002",
    )
    return ArchitectAgent(config)
