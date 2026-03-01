"""
Reviewer Agent - 负责代码审查、质量把控
"""

from typing import Any, Dict, List, Optional
from demo.shared.base_demo_agent import DemoAgent
from usmsb_sdk.agent_sdk import AgentConfig


class ReviewerAgent(DemoAgent):
    """
    代码审查 AI Agent

    职责：
    - 代码审查
    - 质量把控
    - 最佳实践建议
    - 安全漏洞检测
    """

    def __init__(self, config: AgentConfig, visualizer=None):
        super().__init__(config, scenario_name="software_dev", visualizer=visualizer)
        self.reviews: List[Dict] = []
        self.review_standards = {
            "code_style": True,
            "security": True,
            "performance": True,
            "documentation": True,
            "test_coverage": True,
        }

    async def _setup_skills(self):
        """设置技能"""
        self.register_skill(
            name="review_code",
            description="代码审查",
            handler=self._review_code,
            parameters={"code": "代码内容", "task": "任务信息"}
        )

        self.register_skill(
            name="check_security",
            description="安全检查",
            handler=self._check_security,
            parameters={"code": "代码内容"}
        )

        self.register_skill(
            name="suggest_improvements",
            description="改进建议",
            handler=self._suggest_improvements,
            parameters={"code": "代码内容", "issues": "发现的问题"}
        )

    async def _setup_capabilities(self):
        """设置能力"""
        self.register_capability("code_review", "代码审查", 0.95)
        self.register_capability("security_audit", "安全审计", 0.9)
        self.register_capability("best_practices", "最佳实践", 0.85)
        self.register_capability("performance_analysis", "性能分析", 0.8)

    async def _review_code(self, params: Dict) -> Dict:
        """代码审查"""
        code = params.get("code", "")
        task = params.get("task", {})

        self.logger.info(f"🔍 审查代码: {task.get('title', 'unknown')}")

        # 模拟代码审查
        issues = []
        suggestions = []

        # 模拟发现的问题
        if "TODO" in code:
            issues.append("发现未完成的 TODO 注释")

        if "print(" in code:
            suggestions.append("建议使用 logging 替代 print")

        # 模拟安全检查
        if "password" in code.lower() and "hash" not in code.lower():
            issues.append("密码存储应使用哈希")

        # 计算审查结果
        passed = len(issues) == 0

        review_result = {
            "task_id": task.get("id", "unknown"),
            "passed": passed,
            "score": 0.92 if passed else 0.75,
            "issues": issues,
            "suggestions": suggestions,
            "security_concerns": await self._check_security({"code": code}),
            "coverage": 0.92,
            "reviewer": self.name,
        }

        self.reviews.append(review_result)

        self._log_action("review_code", {
            "task_id": task.get("id", "unknown"),
            "passed": passed,
            "issues_count": len(issues)
        })

        return review_result

    async def _check_security(self, params: Dict) -> List[str]:
        """安全检查"""
        code = params.get("code", "")
        concerns = []

        # 模拟安全检查规则
        security_rules = [
            ("sql_injection", "SQL 注入风险", "SELECT" in code and "f\"" in code),
            ("xss", "XSS 风险", "innerHTML" in code),
            ("hardcoded_secrets", "硬编码密钥", "secret" in code.lower() and "=" in code),
        ]

        for rule_id, rule_name, detected in security_rules:
            if detected:
                concerns.append(f"⚠️ {rule_name} ({rule_id})")

        return concerns

    async def _suggest_improvements(self, params: Dict) -> List[str]:
        """改进建议"""
        code = params.get("code", "")
        issues = params.get("issues", [])

        suggestions = []

        # 模拟改进建议
        if len(code.split("\n")) > 100:
            suggestions.append("📝 建议将大函数拆分为更小的函数")

        if "try" not in code and "except" not in code:
            suggestions.append("🛡️ 建议添加异常处理")

        if "docstring" not in code.lower() and '"""' not in code:
            suggestions.append("📚 建议添加文档字符串")

        return suggestions

    async def handle_message(self, message: Any, session=None) -> Any:
        """处理消息"""
        msg = self._wrap_message(message)
        content = self._extract_content(message)

        # 如果收到代码提交
        if isinstance(content, dict) and content.get("type") == "code_submission":
            implementation = content.get("implementation", {})
            task = implementation.get("task_id", {})

            # 进行代码审查
            review_result = await self._review_code({
                "code": implementation.get("code", ""),
                "task": {"id": implementation.get("task_id"), "title": implementation.get("title")}
            })

            # 生成改进建议
            suggestions = await self._suggest_improvements({
                "code": implementation.get("code", ""),
                "issues": review_result.get("issues", [])
            })

            # 如果通过审查，通知 DevOps 部署
            if review_result["passed"]:
                await self.send_message(
                    receiver="DevOps",
                    content={
                        "type": "deploy_request",
                        "implementation": implementation,
                        "review": review_result,
                    },
                    message_type="task"
                )

                return {"status": "approved", "review": review_result}
            else:
                # 反馈给 Developer 修改
                await self.send_message(
                    receiver="Developer",
                    content={
                        "type": "review_feedback",
                        "needs_fix": True,
                        "feedback": review_result["issues"],
                        "suggestions": suggestions,
                    },
                    message_type="task"
                )

                return {"status": "needs_revision", "review": review_result}

        return await super().handle_message(message, session)


def create_reviewer() -> ReviewerAgent:
    """创建 Reviewer Agent"""
    config = AgentConfig(
        name="Reviewer",
        description="代码审查 AI - 负责代码质量和安全审查",
        capabilities=["code_review", "security_audit", "best_practices", "performance_analysis"],
        endpoint="http://localhost:8004",
    )
    return ReviewerAgent(config)
