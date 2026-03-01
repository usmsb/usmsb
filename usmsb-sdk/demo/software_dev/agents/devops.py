"""
DevOps Agent - 负责部署配置、监控告警
"""

from typing import Any, Dict, List, Optional
from demo.shared.base_demo_agent import DemoAgent
from usmsb_sdk.agent_sdk import AgentConfig


class DevOpsAgent(DemoAgent):
    """
    DevOps AI Agent

    职责：
    - CI/CD 配置
    - 环境部署
    - 监控告警
    - 容器编排
    """

    def __init__(self, config: AgentConfig, visualizer=None):
        super().__init__(config, scenario_name="software_dev", visualizer=visualizer)
        self.deployments: List[Dict] = []
        self.environments = {
            "dev": {"url": "http://dev.example.com", "status": "running"},
            "staging": {"url": "http://staging.example.com", "status": "running"},
            "production": {"url": "http://prod.example.com", "status": "running"},
        }
        self.monitoring_alerts: List[Dict] = []

    async def _setup_skills(self):
        """设置技能"""
        self.register_skill(
            name="deploy",
            description="部署应用",
            handler=self._deploy,
            parameters={"environment": "环境名称", "version": "版本号"}
        )

        self.register_skill(
            name="rollback",
            description="回滚部署",
            handler=self._rollback,
            parameters={"environment": "环境名称", "version": "目标版本"}
        )

        self.register_skill(
            name="check_health",
            description="健康检查",
            handler=self._check_health,
            parameters={"service": "服务名称"}
        )

        self.register_skill(
            name="scale",
            description="扩缩容",
            handler=self._scale,
            parameters={"service": "服务名称", "replicas": "副本数"}
        )

    async def _setup_capabilities(self):
        """设置能力"""
        self.register_capability("ci_cd", "CI/CD 配置", 0.9)
        self.register_capability("deployment", "应用部署", 0.95)
        self.register_capability("monitoring", "监控告警", 0.85)
        self.register_capability("containerization", "容器编排", 0.9)

    async def _deploy(self, params: Dict) -> Dict:
        """部署应用"""
        environment = params.get("environment", "staging")
        version = params.get("version", "latest")
        implementation = params.get("implementation", {})

        self.logger.info(f"🚀 部署到 {environment}: v{version}")

        # 模拟部署过程
        deployment_steps = [
            {"step": "build", "status": "success", "duration": "30s"},
            {"step": "test", "status": "success", "duration": "45s"},
            {"step": "push_image", "status": "success", "duration": "20s"},
            {"step": "deploy", "status": "success", "duration": "15s"},
            {"step": "health_check", "status": "success", "duration": "10s"},
        ]

        deployment_result = {
            "id": f"deploy-{len(self.deployments) + 1}",
            "environment": environment,
            "version": version,
            "status": "success",
            "url": self.environments.get(environment, {}).get("url", "unknown"),
            "steps": deployment_steps,
            "total_duration": "120s",
            "replicas": 3,
            "features_deployed": implementation.get("title", "unknown"),
        }

        self.deployments.append(deployment_result)

        self._log_action("deploy", {
            "environment": environment,
            "version": version,
            "status": "success"
        })

        return deployment_result

    async def _rollback(self, params: Dict) -> Dict:
        """回滚部署"""
        environment = params.get("environment", "production")
        target_version = params.get("version", "previous")

        self.logger.warning(f"⏪ 回滚 {environment} 到 {target_version}")

        rollback_result = {
            "environment": environment,
            "target_version": target_version,
            "status": "success",
            "previous_version": "v1.2.3",
            "current_version": target_version,
        }

        self._log_action("rollback", {
            "environment": environment,
            "target_version": target_version
        })

        return rollback_result

    async def _check_health(self, params: Dict) -> Dict:
        """健康检查"""
        service = params.get("service", "all")

        # 模拟健康检查结果
        health_result = {
            "service": service,
            "status": "healthy",
            "checks": {
                "database": {"status": "pass", "latency": "5ms"},
                "cache": {"status": "pass", "latency": "1ms"},
                "api": {"status": "pass", "latency": "20ms"},
                "memory": {"status": "pass", "usage": "45%"},
                "cpu": {"status": "pass", "usage": "30%"},
            },
            "uptime": "99.9%",
        }

        return health_result

    async def _scale(self, params: Dict) -> Dict:
        """扩缩容"""
        service = params.get("service", "api")
        replicas = params.get("replicas", 3)

        self.logger.info(f"📈 扩缩容 {service}: {replicas} 副本")

        scale_result = {
            "service": service,
            "previous_replicas": 2,
            "current_replicas": replicas,
            "status": "success",
        }

        self._log_action("scale", {
            "service": service,
            "replicas": replicas
        })

        return scale_result

    async def notify_product_owner(self, deployment_result: Dict):
        """通知 ProductOwner 部署完成"""
        await self.send_message(
            receiver="ProductOwner",
            content={
                "type": "deployment_complete",
                "deployment": deployment_result,
                "feature_id": deployment_result.get("features_deployed"),
                "environment": deployment_result.get("environment"),
                "url": deployment_result.get("url"),
            },
            message_type="result"
        )

    async def handle_message(self, message: Any, session=None) -> Any:
        """处理消息"""
        msg = self._wrap_message(message)
        content = self._extract_content(message)

        # 如果收到部署请求
        if isinstance(content, dict) and content.get("type") == "deploy_request":
            implementation = content.get("implementation", {})
            review = content.get("review", {})

            # 执行部署
            deployment_result = await self._deploy({
                "environment": "staging",
                "version": "1.0.0",
                "implementation": implementation
            })

            # 健康检查
            health = await self._check_health({"service": "api"})

            # 通知 ProductOwner
            await self.notify_product_owner(deployment_result)

            return {
                "status": "deployed",
                "deployment": deployment_result,
                "health": health
            }

        # 如果收到监控告警
        if isinstance(content, dict) and content.get("type") == "monitoring_alert":
            alert = content.get("alert", {})
            self.monitoring_alerts.append(alert)

            self.logger.warning(f"⚠️ 收到监控告警: {alert.get('message', 'unknown')}")

            # 模拟自动响应
            if alert.get("severity") == "critical":
                # 自动扩容
                await self._scale({"service": "api", "replicas": 5})

            return {"status": "alert_handled", "action": "auto_scaled"}

        return await super().handle_message(message, session)

    def get_deployment_history(self) -> List[Dict]:
        """获取部署历史"""
        return self.deployments

    def get_current_status(self) -> Dict:
        """获取当前状态"""
        return {
            "environments": self.environments,
            "total_deployments": len(self.deployments),
            "alerts_count": len(self.monitoring_alerts),
        }


def create_devops() -> DevOpsAgent:
    """创建 DevOps Agent"""
    config = AgentConfig(
        name="DevOps",
        description="DevOps AI - 负责部署和监控",
        capabilities=["ci_cd", "deployment", "monitoring", "containerization"],
        endpoint="http://localhost:8005",
    )
    return DevOpsAgent(config)
