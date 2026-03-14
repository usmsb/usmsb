"""
Skills Manager - 技能管理器

管理 AI Agent 的技能：
1. 内置技能（内置工具和功能）
2. 外部技能（用户注册的技能）
3. skills.md 格式的技能描述
"""

import asyncio
import json
import logging
import os
import re
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Skill:
    """技能定义"""

    name: str
    description: str
    version: str = "1.0.0"
    author: str = "unknown"
    category: str = "general"
    parameters: dict[str, Any] = field(default_factory=dict)
    returns: str = "string"
    examples: list[str] = field(default_factory=list)
    handler: Callable | None = None
    source: str = "builtin"
    enabled: bool = True
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "category": self.category,
            "parameters": self.parameters,
            "returns": self.returns,
            "examples": self.examples,
            "source": self.source,
            "enabled": self.enabled,
        }

    def to_function_schema(self, provider: str = "anthropic") -> dict[str, Any]:
        """转换为 Function Calling 的 JSON Schema 格式

        Args:
            provider: LLM提供商 (anthropic/openai/ollama)
        """
        # 构建参数 schema
        properties = {}
        required = []

        for param_name, param_info in self.parameters.items():
            if isinstance(param_info, dict):
                properties[param_name] = {
                    "type": param_info.get("type", "string"),
                    "description": param_info.get("description", ""),
                }
                if param_info.get("required"):
                    required.append(param_name)
            else:
                properties[param_name] = {
                    "type": "string",
                    "description": str(param_info),
                }

        if provider == "anthropic":
            # Anthropic Claude 格式
            return {
                "name": self.name,
                "description": self.description,
                "input_schema": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            }
        else:
            # OpenAI 格式 (默认)
            return {
                "type": "function",
                "function": {
                    "name": self.name,
                    "description": self.description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
            }


class SkillsManager:
    """
    技能管理器

    功能：
    1. 加载内置技能
    2. 解析 skills.md 文件
    3. 注册外部技能
    4. 技能调用和执行
    5. 技能权限控制
    """

    def __init__(self, db_path: str = "meta_agent.db"):
        self.db_path = db_path
        self.skills: dict[str, Skill] = {}
        self._initialized = False

    async def init(self):
        """初始化"""
        if self._initialized:
            return

        await self._init_db()
        await self._load_builtin_skills()
        self._initialized = True
        logger.info(f"Skills Manager initialized with {len(self.skills)} skills")

    async def _init_db(self):
        """初始化数据库"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._create_tables)

    def _create_tables(self):
        """创建数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                version TEXT,
                author TEXT,
                category TEXT,
                parameters TEXT,
                returns TEXT,
                examples TEXT,
                source TEXT,
                enabled INTEGER DEFAULT 1,
                created_at REAL,
                metadata TEXT
            )
        """)

        conn.commit()
        conn.close()

    async def _load_builtin_skills(self):
        """加载内置技能"""
        builtin_skills = [
            Skill(
                name="chat",
                description="与用户进行自然语言对话",
                category="interaction",
                parameters={
                    "message": {"type": "string", "description": "用户消息"},
                },
            ),
            Skill(
                name="search",
                description="搜索知识库和互联网信息",
                category="information",
                parameters={
                    "query": {"type": "string", "description": "搜索关键词"},
                    "source": {"type": "string", "description": "数据源：knowledge/web/all"},
                },
            ),
            Skill(
                name="analyze",
                description="分析数据并生成报告",
                category="data",
                parameters={
                    "data": {"type": "any", "description": "待分析数据"},
                    "type": {"type": "string", "description": "分析类型"},
                },
            ),
            Skill(
                name="execute",
                description="执行系统命令或工具",
                category="action",
                parameters={
                    "tool": {"type": "string", "description": "工具名称"},
                    "params": {"type": "object", "description": "工具参数"},
                },
            ),
            Skill(
                name="learn",
                description="从交互中学习新知识",
                category="learning",
                parameters={
                    "content": {"type": "string", "description": "学习内容"},
                    "category": {"type": "string", "description": "知识类别"},
                },
            ),
            Skill(
                name="remember",
                description="记住用户偏好和上下文",
                category="memory",
                parameters={
                    "key": {"type": "string", "description": "记忆键"},
                    "value": {"type": "any", "description": "记忆值"},
                },
            ),
            Skill(
                name="blockchain_query",
                description="查询区块链数据",
                category="blockchain",
                parameters={
                    "method": {"type": "string", "description": "查询方法"},
                    "params": {"type": "object", "description": "查询参数"},
                },
            ),
            Skill(
                name="governance",
                description="参与治理投票",
                category="governance",
                parameters={
                    "action": {"type": "string", "description": "治理操作"},
                    "proposal_id": {"type": "integer", "description": "提案ID"},
                },
            ),
        ]

        for skill in builtin_skills:
            self.skills[skill.name] = skill

    async def load_skills(self):
        """加载所有技能"""
        await self.init()

        loop = asyncio.get_event_loop()
        stored_skills = await loop.run_in_executor(None, self._load_stored_skills)

        for skill_data in stored_skills:
            skill = Skill(
                name=skill_data[1],
                description=skill_data[2] or "",
                version=skill_data[3] or "1.0.0",
                author=skill_data[4] or "unknown",
                category=skill_data[5] or "general",
                parameters=json.loads(skill_data[6]) if skill_data[6] else {},
                returns=skill_data[7] or "string",
                examples=json.loads(skill_data[8]) if skill_data[8] else [],
                source=skill_data[9] or "external",
                enabled=bool(skill_data[10]),
            )
            self.skills[skill.name] = skill

        logger.info(f"Loaded {len(stored_skills)} external skills")

    def _load_stored_skills(self) -> list:
        """加载存储的技能"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM skills WHERE enabled = 1")
        rows = cursor.fetchall()
        conn.close()
        return rows

    async def load_skill(self, skill_path: str):
        """加载单个技能文件（支持 skills.md 格式）"""
        if not os.path.exists(skill_path):
            logger.warning(f"Skill file not found: {skill_path}")
            return

        if skill_path.endswith(".md"):
            await self._load_skill_from_md(skill_path)
        elif skill_path.endswith(".json"):
            await self._load_skill_from_json(skill_path)
        else:
            logger.warning(f"Unsupported skill format: {skill_path}")

    async def _load_skill_from_md(self, file_path: str):
        """从 skills.md 文件解析技能"""
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        skills = self._parse_skills_md(content)

        for skill_data in skills:
            skill = Skill(
                name=skill_data.get("name", "unknown"),
                description=skill_data.get("description", ""),
                category=skill_data.get("category", "general"),
                parameters=skill_data.get("parameters", {}),
                examples=skill_data.get("examples", []),
                source=file_path,
            )

            if skill.name not in self.skills:
                self.skills[skill.name] = skill
                await self._save_skill(skill)
                logger.info(f"Loaded skill from md: {skill.name}")

    def _parse_skills_md(self, content: str) -> list[dict[str, Any]]:
        """解析 skills.md 格式"""
        skills = []

        sections = re.split(r"\n##\s+", content)

        for section in sections[1:]:
            lines = section.strip().split("\n")
            if not lines:
                continue

            skill = {"name": lines[0].strip()}

            for line in lines[1:]:
                line = line.strip()
                if line.startswith("- description:"):
                    skill["description"] = line.replace("- description:", "").strip()
                elif line.startswith("- category:"):
                    skill["category"] = line.replace("- category:", "").strip()
                elif line.startswith("- parameters:"):
                    params_str = line.replace("- parameters:", "").strip()
                    try:
                        skill["parameters"] = json.loads(params_str)
                    except:
                        pass
                elif line.startswith("```"):
                    continue

            if skill.get("name"):
                skills.append(skill)

        return skills

    async def _load_skill_from_json(self, file_path: str):
        """从 JSON 文件加载技能"""
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            for skill_data in data:
                await self._register_skill_from_dict(skill_data, file_path)
        elif isinstance(data, dict):
            await self._register_skill_from_dict(data, file_path)

    async def _register_skill_from_dict(self, data: dict, source: str):
        """从字典注册技能"""
        skill = Skill(
            name=data.get("name", "unknown"),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            author=data.get("author", "unknown"),
            category=data.get("category", "general"),
            parameters=data.get("parameters", {}),
            returns=data.get("returns", "string"),
            examples=data.get("examples", []),
            source=source,
        )

        if skill.name not in self.skills:
            self.skills[skill.name] = skill
            await self._save_skill(skill)
            logger.info(f"Loaded skill from json: {skill.name}")

    async def _save_skill(self, skill: Skill):
        """保存技能到数据库"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._insert_skill, skill)

    def _insert_skill(self, skill: Skill):
        """插入技能"""
        import uuid

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO skills
            (id, name, description, version, author, category, parameters, returns, examples, source, enabled, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                str(uuid.uuid4())[:8],
                skill.name,
                skill.description,
                skill.version,
                skill.author,
                skill.category,
                json.dumps(skill.parameters),
                skill.returns,
                json.dumps(skill.examples),
                skill.source,
                1 if skill.enabled else 0,
                skill.created_at,
            ),
        )

        conn.commit()
        conn.close()

    def get_skill(self, name: str) -> Skill | None:
        """获取技能"""
        return self.skills.get(name)

    def list_skills(self) -> list[str]:
        """列出所有技能名称"""
        return list(self.skills.keys())

    def get_skills_by_category(self, category: str) -> list[Skill]:
        """按类别获取技能"""
        return [s for s in self.skills.values() if s.category == category]

    def get_skills_schema(self, provider: str = "anthropic") -> list[dict[str, Any]]:
        """
        获取所有技能的 JSON Schema 格式（用于 Function Calling）

        Args:
            provider: LLM提供商 (anthropic/openai/ollama)

        Returns:
            技能列表的 Function Calling 格式
        """
        schemas = []
        for skill in self.skills.values():
            schema = skill.to_function_schema(provider)
            schemas.append(schema)
        return schemas

    def get_skills_description(self) -> str:
        """获取所有技能的描述文本"""
        lines = ["## 可用技能\n"]

        categories = {}
        for skill in self.skills.values():
            if skill.category not in categories:
                categories[skill.category] = []
            categories[skill.category].append(skill)

        for category, skills in sorted(categories.items()):
            lines.append(f"\n### {category.upper()}\n")
            for skill in skills:
                lines.append(f"- **{skill.name}**: {skill.description}")
                if skill.examples:
                    lines.append(f"  示例: {skill.examples[0]}")

        return "\n".join(lines)

    async def register_skill(
        self,
        name: str,
        description: str,
        handler: Callable | None = None,
        parameters: dict | None = None,
        category: str = "custom",
    ) -> Skill:
        """注册新技能"""
        skill = Skill(
            name=name,
            description=description,
            handler=handler,
            parameters=parameters or {},
            category=category,
            source="runtime",
        )

        self.skills[name] = skill
        await self._save_skill(skill)

        logger.info(f"Registered skill: {name}")
        return skill

    async def execute_skill(
        self,
        name: str,
        params: dict[str, Any],
    ) -> Any:
        """执行技能"""
        skill = self.skills.get(name)
        if not skill:
            raise ValueError(f"Skill not found: {name}")

        if not skill.enabled:
            raise ValueError(f"Skill is disabled: {name}")

        if skill.handler:
            if asyncio.iscoroutinefunction(skill.handler):
                return await skill.handler(**params)
            else:
                return skill.handler(**params)

        return {"status": "skill_executed", "name": name, "params": params}
