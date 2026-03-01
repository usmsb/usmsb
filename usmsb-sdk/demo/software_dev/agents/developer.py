"""
Developer Agent - 负责代码实现和测试
"""

from typing import Any, Dict, List, Optional
from demo.shared.base_demo_agent import DemoAgent, DemoMessage
from usmsb_sdk.agent_sdk import AgentConfig


class DeveloperAgent(DemoAgent):
    """
    开发者 AI Agent

    职责：
    - 代码实现
    - 单元测试
    - Bug 修复
    - 技术文档
    """

    def __init__(self, config: AgentConfig, visualizer=None):
        super().__init__(config, scenario_name="software_dev", visualizer=visualizer)
        self.implementations: List[Dict] = []
        self.current_task: Optional[Dict] = None
        self.code_submissions: List[Dict] = []

    async def _setup_skills(self):
        """设置技能"""
        self.register_skill(
            name="implement_feature",
            description="实现功能",
            handler=self._implement_feature,
            parameters={"task": "任务描述", "design": "设计方案"}
        )

        self.register_skill(
            name="write_tests",
            description="编写测试",
            handler=self._write_tests,
            parameters={"code": "代码内容", "feature": "功能名称"}
        )

        self.register_skill(
            name="fix_bug",
            description="修复 Bug",
            handler=self._fix_bug,
            parameters={"bug_description": "Bug 描述", "code": "相关代码"}
        )

    async def _setup_capabilities(self):
        """设置能力"""
        self.register_capability("coding", "编码实现", 0.9)
        self.register_capability("testing", "单元测试", 0.85)
        self.register_capability("debugging", "调试排错", 0.8)
        self.register_capability("documentation", "技术文档", 0.75)

    async def _implement_feature(self, params: Dict) -> Dict:
        """实现功能"""
        task = params.get("task", {})
        design = params.get("design", {})

        task_id = task.get("id", "unknown")
        task_title = task.get("title", "未命名任务")

        self.logger.info(f"🔨 实现功能: {task_title}")

        # 模拟代码实现
        implementation = {
            "task_id": task_id,
            "title": task_title,
            "code": self._generate_mock_code(task, design),
            "tests": [],
            "status": "implemented",
            "lines_of_code": 150,
            "files_changed": ["main.py", "models.py", "api.py"],
        }

        # 自动编写测试
        tests = await self._write_tests({
            "code": implementation["code"],
            "feature": task_title
        })
        implementation["tests"] = tests.get("test_cases", [])

        self.implementations.append(implementation)
        self.current_task = implementation

        self._log_action("implement_feature", {
            "task_id": task_id,
            "lines_of_code": implementation["lines_of_code"]
        })

        return implementation

    async def _write_tests(self, params: Dict) -> Dict:
        """编写测试"""
        feature = params.get("feature", "功能")

        # 模拟测试用例
        test_cases = [
            {"name": f"test_{feature}_success", "type": "unit", "status": "pass"},
            {"name": f"test_{feature}_error", "type": "unit", "status": "pass"},
            {"name": f"test_{feature}_edge_case", "type": "unit", "status": "pass"},
            {"name": f"test_{feature}_integration", "type": "integration", "status": "pass"},
        ]

        result = {
            "feature": feature,
            "test_cases": test_cases,
            "coverage": 0.92,
            "all_passed": all(t["status"] == "pass" for t in test_cases),
        }

        self._log_action("write_tests", {
            "feature": feature,
            "tests_count": len(test_cases),
            "coverage": result["coverage"]
        })

        return result

    async def _fix_bug(self, params: Dict) -> Dict:
        """修复 Bug"""
        bug_description = params.get("bug_description", "")

        # 模拟 Bug 修复
        fix_result = {
            "bug": bug_description,
            "fixed": True,
            "changes": ["修复了空指针异常", "添加了边界检查"],
            "tests_added": 2,
        }

        self._log_action("fix_bug", {
            "bug": bug_description[:50],
            "fixed": fix_result["fixed"]
        })

        return fix_result

    def _generate_mock_code(self, task: Dict, design: Dict) -> str:
        """生成模拟代码"""
        task_title = task.get("title", "未命名")

        code = f'''"""
{task_title}

自动生成的代码示例
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class {task_title.replace(" ", "")}Request(BaseModel):
    """请求模型"""
    user_id: str
    data: dict


class {task_title.replace(" ", "")}Response(BaseModel):
    """响应模型"""
    success: bool
    message: str
    result: Optional[dict] = None


@router.post("/api/{task_title.lower().replace(' ', '-')}")
async def {task_title.lower().replace(' ', '_')}(request: {task_title.replace(" ", "")}Request):
    """
    {task_title} API
    """
    try:
        # 业务逻辑
        result = {{"processed": True, "user_id": request.user_id}}

        return {task_title.replace(" ", "")}Response(
            success=True,
            message="操作成功",
            result=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
'''
        return code

    async def submit_code(self, implementation: Dict) -> DemoMessage:
        """提交代码给 Reviewer"""
        self.logger.info(f"📤 提交代码: {implementation.get('task_id', 'unknown')}")

        submission = {
            "type": "code_submission",
            "implementation": implementation,
            "submitted_at": self._get_timestamp(),
            "author": self.name,
        }

        self.code_submissions.append(submission)

        msg = await self.send_message(
            receiver="Reviewer",
            content=submission,
            message_type="task"
        )

        return msg

    async def handle_message(self, message: Any, session=None) -> Any:
        """处理消息"""
        msg = self._wrap_message(message)
        content = self._extract_content(message)

        # 如果收到技术设计
        if isinstance(content, dict) and content.get("type") == "technical_design":
            tasks = content.get("tasks", [])
            design = content.get("design", {})

            results = []
            for task in tasks[:2]:  # 只处理前2个任务作为演示
                implementation = await self._implement_feature({
                    "task": task,
                    "design": design
                })
                results.append(implementation)

                # 提交代码
                await self.submit_code(implementation)

            return {"status": "implementations_completed", "count": len(results)}

        # 如果收到审查反馈
        if isinstance(content, dict) and content.get("type") == "review_feedback":
            feedback = content.get("feedback", [])
            needs_fix = content.get("needs_fix", False)

            if needs_fix:
                # 修复问题
                for issue in feedback:
                    await self._fix_bug({"bug_description": issue})

                # 重新提交
                if self.current_task:
                    await self.submit_code(self.current_task)
                    return {"status": "resubmitted"}

            return {"status": "acknowledged"}

        return await super().handle_message(message, session)

    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()


def create_developer() -> DeveloperAgent:
    """创建 Developer Agent"""
    config = AgentConfig(
        name="Developer",
        description="开发者 AI - 负责代码实现和测试",
        capabilities=["coding", "testing", "debugging", "documentation"],
        endpoint="http://localhost:8003",
    )
    return DeveloperAgent(config)
