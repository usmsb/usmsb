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

from .skill_loader import (
    SkillFolder,
    load_skill_folder,
    load_all_skills_from_directory,
)

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

    def __init__(self, db_path: str = "meta_agent.db", skills_dir: str = ""):
        self.db_path = db_path
        self.skills_dir = skills_dir
        self.skills: dict[str, Skill] = {}
        self._skill_folders: dict[str, SkillFolder] = {}  # file-based skills
        self._tool_registry = None  # 引用 ToolRegistry 用于 Skills meta-skill
        self._initialized = False

    async def init(self):
        """初始化"""
        if self._initialized:
            return

        await self._init_db()
        await self._load_builtin_skills()
        await self._register_skills_meta_skill()
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

    async def _register_skills_meta_skill(self):
        """注册 Skills meta-skill（列出所有可用技能和工具）"""

        async def skills_meta_handler(params: dict = None, session: "UserSession" = None) -> dict:
            """列出所有可用技能和工具（增强版）

            Args:
                params: 请求参数
                session: 用户会话（可选）

            Returns:
                包含所有 skills 和 tools 的列表
            """
            # 1. 获取所有 file-based skills（从 _skill_folders）
            file_skills = []
            for name, folder in self._skill_folders.items():
                file_skills.append({
                    "name": folder.name,
                    "description": folder.description,
                    "category": folder.category,
                    "version": folder.version,
                    "source": "file",
                })

            # 2. 获取所有 runtime/builtin skills（从 self.skills，排除 meta-skills 自身）
            runtime_skills = []
            for skill in self.skills.values():
                if skill.source in ("runtime", "builtin") and skill.name != "Skills":
                    runtime_skills.append({
                        "name": skill.name,
                        "description": skill.description,
                        "category": skill.category,
                        "version": skill.version,
                        "source": skill.source,
                        "has_handler": skill.handler is not None,
                    })

            # 3. 获取所有 ToolRegistry tools（如果可用）
            tools = []
            if self._tool_registry:
                try:
                    for tool_info in self._tool_registry.list_tools():
                        tools.append({
                            "name": tool_info["name"],
                            "description": tool_info.get("description", ""),
                        })
                except Exception as e:
                    logger.warning(f"Failed to get tools from ToolRegistry: {e}")

            return {
                "skills_file": file_skills,
                "skills_runtime": runtime_skills,
                "tools": tools,
                "summary": {
                    "total_skills_file": len(file_skills),
                    "total_skills_runtime": len(runtime_skills),
                    "total_tools": len(tools),
                },
            }

        self.skills["Skills"] = Skill(
            name="Skills",
            description="列出所有可用的 Agent Skills 和 Tools。当用户询问你能做什么，或者需要了解有哪些可用能力时使用此技能。这是 Agent Skills 标准的 Discovery 机制。",
            category="meta",
            version="1.0.0",
            author="usmsb",
            parameters={},  # 不需要参数
            handler=skills_meta_handler,
            source="builtin",
        )
        logger.debug("Registered Skills meta-skill")

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

    def set_tool_registry(self, tool_registry):
        """设置 ToolRegistry 引用（用于 Skills meta-skill）"""
        self._tool_registry = tool_registry

    def load_skills_from_directory(self, skills_dir: str = ""):
        """Discovery: 扫描并加载所有 skill 文件夹（Agent Skills 标准）

        Args:
            skills_dir: skills 目录路径，为空则使用 self.skills_dir
        """
        target_dir = skills_dir or self.skills_dir
        if not target_dir or not os.path.isdir(target_dir):
            logger.debug(f"Skills directory not found: {target_dir}")
            return

        self._skill_folders = load_all_skills_from_directory(target_dir)
        logger.info(f"Loaded {len(self._skill_folders)} skill folders from {target_dir}")

        # 将 file-based skills 转换为 Skill 对象（不带 handler）
        for name, folder in self._skill_folders.items():
            if name not in self.skills:
                skill = Skill(
                    name=folder.name,
                    description=folder.description,
                    version=folder.version,
                    author=folder.author,
                    category=folder.category,
                    source="file",
                    handler=None,  # file-based skills 通过 LLM 理解执行，不走 handler
                )
                self.skills[name] = skill

    async def activate_skill(
        self, skill_name: str, include_scripts: bool = True, include_references: bool = True
    ) -> dict[str, Any]:
        """Activation: 按需加载完整 SKILL.md 内容到 context（Agent Skills 标准）

        当任务匹配 skill 的 description 或 triggers 时调用此方法。

        Args:
            skill_name: 技能名称
            include_scripts: 是否包含脚本内容
            include_references: 是否包含参考文档内容

        Returns:
            activation_result {
                "skill_name": str,
                "instructions": str,       # SKILL.md 完整内容
                "scripts": list[str],      # 可执行脚本列表
                "scripts_content": dict,   # 脚本名称 -> 内容（如果 include_scripts=True）
                "references": dict,        # 参考文档名称 -> 内容（如果 include_references=True）
                "triggers": list[str],     # 触发条件
            }
        """
        folder = self._skill_folders.get(skill_name)
        if not folder:
            return {"error": f"Skill not found: {skill_name}"}

        result = {
            "skill_name": folder.name,
            "description": folder.description,
            "instructions": folder.skill_md_content or folder.instructions,
            "scripts": folder.scripts,
            "references": list(folder.references.keys()),
            "triggers": folder.triggers,
        }

        if include_scripts:
            result["scripts_content"] = folder.get_scripts_content()

        if include_references:
            result["references_content"] = folder.get_references_content()

        return result

    def get_skill_info(self, skill_name: str) -> dict[str, Any] | None:
        """返回 skill 的基本信息（用于 Skills meta-skill）

        Args:
            skill_name: 技能名称

        Returns:
            {name, description, category, version, author, source} 或 None
        """
        # 先查 file-based skills
        folder = self._skill_folders.get(skill_name)
        if folder:
            return {
                "name": folder.name,
                "description": folder.description,
                "category": folder.category,
                "version": folder.version,
                "author": folder.author,
                "source": "file",
                "triggers": folder.triggers,
            }

        # 再查 runtime/builtin skills
        skill = self.skills.get(skill_name)
        if skill:
            return {
                "name": skill.name,
                "description": skill.description,
                "category": skill.category,
                "version": skill.version,
                "author": skill.author,
                "source": skill.source,
            }

        return None

    async def execute_skill_script(
        self, skill_name: str, script_path: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Execution: 执行 skill 的 bundled script

        Args:
            skill_name: 技能名称
            script_path: 脚本路径（相对于 skill/scripts/ 目录）
            params: 脚本参数

        Returns:
            执行结果
        """
        folder = self._skill_folders.get(skill_name)
        if not folder:
            return {"error": f"Skill not found: {skill_name}"}

        full_script_path = os.path.join(folder.scripts_dir, script_path)
        if not os.path.exists(full_script_path):
            return {"error": f"Script not found: {script_path}"}

        # 简单脚本执行：读取内容返回（实际执行由调用方通过 ToolRegistry 执行）
        try:
            with open(full_script_path, encoding="utf-8") as f:
                content = f.read()
            return {
                "status": "script_loaded",
                "skill_name": skill_name,
                "script_path": script_path,
                "content": content,
                "params": params,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_skills_catalog(self) -> str:
        """生成 Skills 目录（用于 System Prompt 注入）

        返回所有 file-based skills 的名称和描述，
        让 LLM 知道有哪些 skill 可用，以及在什么情况下使用。

        Returns:
            格式化的 skills 目录字符串
        """
        if not self._skill_folders:
            return ""

        lines = ["\n\n## 可用 Skills (Agent Skills)\n"]
        lines.append("你可以使用以下技能来完成特定任务。当用户请求涉及以下场景时，调用对应的 skill：\n")

        for name, folder in sorted(self._skill_folders.items()):
            lines.append(f"### {name}")
            lines.append(f"- **描述**: {folder.description}")
            if folder.triggers:
                lines.append(f"- **触发条件**: {'; '.join(folder.triggers[:3])}")
            if folder.category:
                lines.append(f"- **类别**: {folder.category}")
            lines.append("")

        # 添加使用提示
        lines.append("\n**使用方式**: 当需要使用某个 skill 时，调用 `activate_skill` 工具并指定 skill 名称。\n")

        return "\n".join(lines)

    def get_skills_schema(self, provider: str = "anthropic") -> list[dict[str, Any]]:
        """
        获取所有技能的 JSON Schema 格式（用于 Function Calling）

        Agent Skills Discovery 阶段：只返回有 handler 的技能，
        因为只有这些才能通过 execute_skill() 执行。

        注意：file-based skills 不返回 schema（它们通过 activate_skill 加载指令，
        由 LLM 理解后自行决定调用哪些工具，不走 execute_skill 路径）。

        Args:
            provider: LLM提供商 (anthropic/openai/ollama)

        Returns:
            技能列表的 Function Calling 格式
        """
        schemas = []
        for skill in self.skills.values():
            if not skill.enabled:
                continue
            # 只返回有 handler 的 skill（runtime/builtin）
            # file-based skills 通过 activate_skill() 加载，不直接调用
            if skill.handler is None:
                continue
            schema = skill.to_function_schema(provider)
            schemas.append(schema)
        return schemas

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
        session: Any = None,
    ) -> Any:
        """执行技能

        Args:
            name: 技能名称
            params: 技能参数
            session: 可选的 UserSession（用于需要会话上下文的技能）
        """
        skill = self.skills.get(name)
        if not skill:
            raise ValueError(f"Skill not found: {name}")

        if not skill.enabled:
            raise ValueError(f"Skill is disabled: {name}")

        if skill.handler:
            # 构建 handler 参数
            handler_kwargs = params.copy() if params else {}
            if session is not None:
                handler_kwargs["session"] = session

            if asyncio.iscoroutinefunction(skill.handler):
                return await skill.handler(**handler_kwargs)
            else:
                return skill.handler(**handler_kwargs)

        return {"status": "skill_executed", "name": name, "params": params}
