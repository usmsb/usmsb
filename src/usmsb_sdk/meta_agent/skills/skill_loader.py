"""
Skill Loader - 加载 Agent Skills 标准格式的技能文件夹

Agent Skills 格式：
skill_name/
├── SKILL.md          # 必需：元数据 + 指令
├── scripts/          # 可选：可执行脚本
├── references/       # 可选：参考文档
└── assets/          # 可选：资源文件
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SkillFolder:
    """已加载的技能文件夹"""

    name: str
    description: str
    version: str = "1.0.0"
    author: str = "unknown"
    category: str = "general"
    triggers: list[str] = field(default_factory=list)
    instructions: str = ""
    skill_md_path: str = ""
    skill_md_content: str = ""
    scripts_dir: str = ""
    references_dir: str = ""
    assets_dir: str = ""
    scripts: list[str] = field(default_factory=list)  # 可执行脚本列表
    references: dict[str, str] = field(default_factory=dict)  # name -> path
    source: str = "file"  # file | runtime | builtin
    handler: Any = None
    enabled: bool = True

    def get_scripts_content(self) -> dict[str, str]:
        """获取所有脚本的内容"""
        result = {}
        for script_name in self.scripts:
            script_path = os.path.join(self.scripts_dir, script_name)
            if os.path.exists(script_path):
                try:
                    with open(script_path, encoding="utf-8") as f:
                        result[script_name] = f.read()
                except Exception:
                    result[script_name] = f"# Unable to read {script_path}"
        return result

    def get_references_content(self) -> dict[str, str]:
        """获取所有参考文档的内容"""
        result = {}
        for ref_name, ref_path in self.references.items():
            if os.path.exists(ref_path):
                try:
                    with open(ref_path, encoding="utf-8") as f:
                        result[ref_name] = f.read()
                except Exception:
                    result[ref_name] = f"# Unable to read {ref_path}"
        return result


def parse_skill_md(skill_md_path: str) -> dict[str, Any]:
    """解析 SKILL.md 文件，提取元数据和内容

    Args:
        skill_md_path: SKILL.md 文件路径

    Returns:
        包含 name, description, version, author, category, triggers, instructions 的字典
    """
    if not os.path.exists(skill_md_path):
        return {}

    with open(skill_md_path, encoding="utf-8") as f:
        content = f.read()

    return parse_skill_md_content(content, skill_md_path)


def parse_skill_md_content(content: str, source_path: str = "") -> dict[str, Any]:
    """解析 SKILL.md 内容字符串

    Agent Skills 标准格式：
    # Skill Name

    ## Metadata
    - **Name**: example_skill
    - **Description**: What this skill does
    - **Version**: 1.0.0
    - **Author**: Team Name
    - **Category**: coding | data | blockchain | meta

    ## Triggers
    When should this skill be activated?
    - User asks about X
    - Task involves Y

    ## Instructions
    Step-by-step guide...

    ## Scripts (optional)
    Available scripts in `scripts/`:
    - `run.sh` - Execute the main workflow

    ## References (optional)
    - `references/api_docs.md` - API documentation
    """
    result = {
        "name": "",
        "description": "",
        "version": "1.0.0",
        "author": "unknown",
        "category": "general",
        "triggers": [],
        "instructions": "",
        "skill_md_content": content,
        "skill_md_path": source_path,
    }

    lines = content.split("\n")
    current_section = ""

    for line in lines:
        stripped = line.strip()

        # 标题行
        if stripped.startswith("# "):
            # 第一级标题是 skill name
            if not result["name"]:
                result["name"] = stripped[2:].strip()
        elif stripped.startswith("## "):
            current_section = stripped[3:].strip()
        elif stripped.startswith("### "):
            current_section = stripped[4:].strip()
        # Metadata 部分
        elif current_section == "Metadata" and stripped.startswith("-"):
            if "**Name**:" in stripped:
                name = re.search(r"\*\*Name\*\*:\s*(.+)", stripped)
                if name:
                    result["name"] = name.group(1).strip()
            elif "**Description**:" in stripped:
                desc = re.search(r"\*\*Description\*\*:\s*(.+)", stripped)
                if desc:
                    result["description"] = desc.group(1).strip()
            elif "**Version**:" in stripped:
                ver = re.search(r"\*\*Version\*\*:\s*(.+)", stripped)
                if ver:
                    result["version"] = ver.group(1).strip()
            elif "**Author**:" in stripped:
                author = re.search(r"\*\*Author\*\*:\s*(.+)", stripped)
                if author:
                    result["author"] = author.group(1).strip()
            elif "**Category**:" in stripped:
                cat = re.search(r"\*\*Category\*\*:\s*(.+)", stripped)
                if cat:
                    result["category"] = cat.group(1).strip()
        # Triggers 部分
        elif current_section == "Triggers":
            if stripped.startswith("- "):
                trigger = stripped[2:].strip()
                if trigger:
                    result["triggers"].append(trigger)
        # Instructions 部分
        elif current_section == "Instructions":
            result["instructions"] += line + "\n"
        # Scripts 部分
        elif current_section == "Scripts":
            if stripped.startswith("- `") or stripped.startswith("- "):
                # 提取脚本名
                match = re.search(r"`([^`]+)`", stripped)
                if match:
                    script_name = match.group(1)
                    if " - " in stripped:
                        desc = stripped.split(" - ", 1)[1].strip()
                    else:
                        desc = script_name
                    if "scripts" not in result:
                        result["scripts"] = []
                    result["scripts"].append(script_name)
        # References 部分
        elif current_section == "References":
            if stripped.startswith("- "):
                ref_match = re.search(r"`([^`]+)`", stripped)
                if ref_match:
                    ref_path = ref_match.group(1)
                    desc = stripped.split(" - ", 1)[1].strip() if " - " in stripped else ref_path
                    if "references" not in result:
                        result["references"] = {}
                    result["references"][ref_path] = desc

    return result


def scan_scripts_dir(scripts_dir: str) -> list[str]:
    """扫描 scripts 目录，返回可执行脚本列表

    Args:
        scripts_dir: scripts 目录路径

    Returns:
        脚本文件名列表
    """
    if not os.path.isdir(scripts_dir):
        return []

    scripts = []
    for filename in os.listdir(scripts_dir):
        filepath = os.path.join(scripts_dir, filename)
        if os.path.isfile(filepath):
            # 排除隐藏文件和常见不可执行文件
            if not filename.startswith("."):
                scripts.append(filename)
    return sorted(scripts)


def scan_references_dir(references_dir: str) -> dict[str, str]:
    """扫描 references 目录，返回参考文档映射

    Args:
        references_dir: references 目录路径

    Returns:
        {filename: description} 字典
    """
    if not os.path.isdir(references_dir):
        return {}

    references = {}
    for root, _, files in os.walk(references_dir):
        for filename in files:
            if filename.startswith("."):
                continue
            filepath = os.path.join(root, filename)
            rel_path = os.path.relpath(filepath, references_dir)
            # 构建相对路径描述
            references[rel_path] = rel_path
    return references


def load_skill_folder(skill_folder_path: str) -> SkillFolder | None:
    """加载完整的技能文件夹

    Args:
        skill_folder_path: 技能文件夹路径（包含 SKILL.md）

    Returns:
        SkillFolder 对象，或 None（如果加载失败）
    """
    skill_md_path = os.path.join(skill_folder_path, "SKILL.md")
    if not os.path.exists(skill_md_path):
        return None

    # 解析 SKILL.md
    parsed = parse_skill_md(skill_md_path)
    if not parsed.get("name"):
        # 尝试用文件夹名作为 skill name
        parsed["name"] = os.path.basename(skill_folder_path)

    # 确定各目录路径
    scripts_dir = os.path.join(skill_folder_path, "scripts")
    references_dir = os.path.join(skill_folder_path, "references")
    assets_dir = os.path.join(skill_folder_path, "assets")

    # 扫描 scripts 和 references
    scripts = scan_scripts_dir(scripts_dir) if os.path.isdir(scripts_dir) else []
    references = scan_references_dir(references_dir) if os.path.isdir(references_dir) else {}

    return SkillFolder(
        name=parsed["name"],
        description=parsed.get("description", ""),
        version=parsed.get("version", "1.0.0"),
        author=parsed.get("author", "unknown"),
        category=parsed.get("category", "general"),
        triggers=parsed.get("triggers", []),
        instructions=parsed.get("instructions", ""),
        skill_md_path=skill_md_path,
        skill_md_content=parsed.get("skill_md_content", ""),
        scripts_dir=scripts_dir,
        references_dir=references_dir,
        assets_dir=assets_dir,
        scripts=scripts,
        references=references,
        source="file",
    )


def load_all_skills_from_directory(skills_root_dir: str) -> dict[str, SkillFolder]:
    """从根目录加载所有技能文件夹

    Args:
        skills_root_dir: skills 根目录（如 "skills/"）

    Returns:
        {skill_name: SkillFolder} 字典
    """
    if not os.path.isdir(skills_root_dir):
        return {}

    skill_folders = {}
    for entry in os.listdir(skills_root_dir):
        folder_path = os.path.join(skills_root_dir, entry)
        if os.path.isdir(folder_path):
            skill_folder = load_skill_folder(folder_path)
            if skill_folder:
                skill_folders[skill_folder.name] = skill_folder

    return skill_folders
