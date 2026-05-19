"""
Skill 清理器

AutoSkillEngine 的组件

定期管理和清理 skill 库
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class SkillCurator:
    """
    Skill 管理者

    定期管理和清理 skill 库：
    1. 清理低质量 / 未使用的 skill
    2. 解决 skill 冲突
    3. 合并重复的 skill
    4. 版本管理，支持回滚
    """

    def __init__(
        self,
        skill_registry,
        causal_graph=None,
        cleanup_interval: int = 86400,  # 每天清理一次
    ):
        """
        初始化

        Args:
            skill_registry: Skill 注册表
            causal_graph: 因果图
            cleanup_interval: 清理间隔（秒）
        """
        self.registry = skill_registry
        self.graph = causal_graph
        self.cleanup_interval = cleanup_interval
        self._last_cleanup = 0.0

    async def run_curation(self) -> dict[str, Any]:
        """
        执行 curation 循环

        Returns:
            清理报告
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "low_quality_archived": 0,
            "unused_archived": 0,
            "conflicts_resolved": 0,
            "duplicates_merged": 0,
        }

        # 1. 发现低质量 skill
        low_quality = await self._find_low_quality_skills()
        for skill_id in low_quality:
            await self._archive_skill(skill_id)
            report["low_quality_archived"] += 1

        # 2. 发现未使用 skill
        unused = await self._find_unused_skills()
        for skill_id in unused:
            await self._archive_skill(skill_id)
            report["unused_archived"] += 1

        # 3. 发现冲突 skill
        conflicts = await self._find_conflicting_skills()
        for conflict_pair in conflicts:
            resolved = await self._resolve_conflict(conflict_pair)
            if resolved:
                report["conflicts_resolved"] += 1

        # 4. 发现重复 skill
        duplicates = await self._find_duplicates()
        for duplicate_group in duplicates:
            merged = await self._merge_duplicates(duplicate_group)
            if merged:
                report["duplicates_merged"] += 1

        logger.info(f"Skill curation completed: {report}")

        return report

    async def _find_low_quality_skills(self) -> list[str]:
        """
        发现低质量 skill

        指标：
        - 质量评分 < 0.5
        - 错误率 > 30%
        - 用户评分 < 3.0
        """
        low_quality = []

        for skill_id, skill in self.registry.items():
            quality_score = getattr(skill, "quality_score", 0.5)
            error_rate = getattr(skill, "error_rate", 0.0)
            avg_rating = getattr(skill, "avg_rating", 0.0)
            rating_count = getattr(skill, "rating_count", 0)

            if quality_score < 0.5:
                low_quality.append(skill_id)
                continue

            if error_rate > 0.3:
                low_quality.append(skill_id)
                continue

            if rating_count > 10 and avg_rating < 3.0:
                low_quality.append(skill_id)

        return low_quality

    async def _find_unused_skills(self) -> list[str]:
        """发现未使用 skill"""
        unused = []

        for skill_id, skill in self.registry.items():
            usage_count = getattr(skill, "usage_count", 0)

            # 超过 30 天未使用
            last_used = getattr(skill, "last_used_at", None)
            if last_used:
                import time
                days_since_use = (time.time() - last_used) / 86400
                if days_since_use > 30 and usage_count < 5:
                    unused.append(skill_id)

        return unused

    async def _find_conflicting_skills(self) -> list[tuple[str, str]]:
        """发现冲突的 skill"""
        conflicts = []

        skills = list(self.registry.items())

        for i, (id1, skill1) in enumerate(skills):
            for id2, skill2 in skills[i + 1:]:
                if self._skills_conflict(skill1, skill2):
                    conflicts.append((id1, id2))

        return conflicts

    def _skills_conflict(self, skill1, skill2) -> bool:
        """检查两个 skill 是否冲突"""
        # 检查触发条件是否重叠
        triggers1 = set(getattr(skill1, "trigger_conditions", []))
        triggers2 = set(getattr(skill2, "trigger_conditions", []))

        if triggers1 & triggers2:  # 有重叠的触发条件
            # 检查功能是否相反
            desc1 = getattr(skill1, "description", "").lower()
            desc2 = getattr(skill2, "description", "").lower()

            # 简化的冲突检测
            if ("not" in desc1 and "not" not in desc2) or (
                "not" in desc2 and "not" in desc1
            ):
                return True

        return False

    async def _find_duplicates(self) -> list[list[str]]:
        """发现重复的 skill"""
        duplicates = []

        # 按名称相似度分组
        by_name = {}

        for skill_id, skill in self.registry.items():
            name = getattr(skill, "name", "")
            if name:
                # 简化的相似度检测
                key = name.lower().split()[0]
                if key not in by_name:
                    by_name[key] = []
                by_name[key].append(skill_id)

        for skill_ids in by_name.values():
            if len(skill_ids) > 1:
                duplicates.append(skill_ids)

        return duplicates

    async def _archive_skill(self, skill_id: str) -> None:
        """
        归档 skill

        Args:
            skill_id: Skill ID
        """
        if skill_id in self.registry:
            skill = self.registry[skill_id]
            # 设置为不活跃
            setattr(skill, "is_active", False)
            setattr(skill, "archived_at", datetime.now().timestamp())
            logger.info(f"Archived skill: {skill_id}")

    async def _resolve_conflict(self, conflict_pair: tuple[str, str]) -> bool:
        """
        解决冲突

        Args:
            conflict_pair: 冲突的 skill ID 对

        Returns:
            是否解决
        """
        id1, id2 = conflict_pair

        if id1 not in self.registry or id2 not in self.registry:
            return False

        skill1 = self.registry[id1]
        skill2 = self.registry[id2]

        # 选择质量更高的
        quality1 = getattr(skill1, "quality_score", 0.5)
        quality2 = getattr(skill2, "quality_score", 0.5)

        to_archive = id2 if quality1 > quality2 else id1

        await self._archive_skill(to_archive)

        return True

    async def _merge_duplicates(self, duplicate_group: list[str]) -> bool:
        """
        合并重复的 skill

        Args:
            duplicate_group: 重复的 skill ID 列表

        Returns:
            是否合并
        """
        if len(duplicate_group) < 2:
            return False

        # 选择最完整的作为主 skill
        main_id = duplicate_group[0]
        main_skill = self.registry.get(main_id)

        if not main_skill:
            return False

        # 合并其他 skill 的信息
        for skill_id in duplicate_group[1:]:
            if skill_id in self.registry:
                skill = self.registry[skill_id]

                # 合并使用统计
                main_usage = getattr(main_skill, "usage_count", 0)
                other_usage = getattr(skill, "usage_count", 0)
                setattr(main_skill, "usage_count", main_usage + other_usage)

                # 归档其他
                await self._archive_skill(skill_id)

        return True
