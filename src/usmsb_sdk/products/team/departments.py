# -*- coding: utf-8 -*-
"""
Departments - 部门 Agents 系统

每个部门有自己的专业 Agent。

部门：
- Engineering: 工程部
- Design: 设计部
- Product: 产品部
- Marketing: 市场部
- Operations: 运营部
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DepartmentAgent:
    """部门 Agent"""
    id: str
    name: str
    department: str
    role: str  # agent, lead, specialist
    capabilities: list[str] = field(default_factory=list)
    current_task: str | None = None
    status: str = "available"  # available, busy, offline
    performance_score: float = 0.5


class EngineeringDepartment:
    """工程部"""
    
    @staticmethod
    def get_agents() -> list[DepartmentAgent]:
        return [
            DepartmentAgent(
                id="eng_frontend",
                name="前端工程师",
                department="engineering",
                role="agent",
                capabilities=["React", "TypeScript", "CSS", "UI开发"]
            ),
            DepartmentAgent(
                id="eng_backend",
                name="后端工程师",
                department="engineering",
                role="agent",
                capabilities=["Python", "FastAPI", "SQL", "API设计"]
            ),
            DepartmentAgent(
                id="eng_infra",
                name="运维工程师",
                department="engineering",
                role="agent",
                capabilities=["Docker", "Kubernetes", "CI/CD", "Linux"]
            ),
            DepartmentAgent(
                id="eng_ai",
                name="AI 工程师",
                department="engineering",
                role="agent",
                capabilities=["LLM", "Agent", "RAG", "向量数据库"]
            ),
        ]
    
    @staticmethod
    def get_lead() -> DepartmentAgent:
        return DepartmentAgent(
            id="eng_lead",
            name="工程总监",
            department="engineering",
            role="lead",
            capabilities=["架构设计", "技术选型", "代码审查", "团队管理"]
        )


class DesignDepartment:
    """设计部"""
    
    @staticmethod
    def get_agents() -> list[DepartmentAgent]:
        return [
            DepartmentAgent(
                id="des_ui",
                name="UI 设计师",
                department="design",
                role="agent",
                capabilities=["Figma", "UI设计", "原型", "设计系统"]
            ),
            DepartmentAgent(
                id="des_ux",
                name="UX 设计师",
                department="design",
                role="agent",
                capabilities=["用户研究", "交互设计", "可用性测试", "信息架构"]
            ),
            DepartmentAgent(
                id="des_brand",
                name="品牌设计师",
                department="design",
                role="agent",
                capabilities=["品牌设计", "视觉识别", "海报设计", "插画"]
            ),
        ]
    
    @staticmethod
    def get_lead() -> DepartmentAgent:
        return DepartmentAgent(
            id="des_lead",
            name="设计总监",
            department="design",
            role="lead",
            capabilities=["设计管理", "创意指导", "团队协作", "品牌战略"]
        )


class ProductDepartment:
    """产品部"""
    
    @staticmethod
    def get_agents() -> list[DepartmentAgent]:
        return [
            DepartmentAgent(
                id="prod_pm",
                name="产品经理",
                department="product",
                role="agent",
                capabilities=["需求分析", "PRD撰写", "项目管理", "数据分析"]
            ),
            DepartmentAgent(
                id="prod_research",
                name="用户研究员",
                department="product",
                role="agent",
                capabilities=["用户访谈", "市场调研", "竞品分析", "数据挖掘"]
            ),
        ]
    
    @staticmethod
    def get_lead() -> DepartmentAgent:
        return DepartmentAgent(
            id="prod_lead",
            name="产品总监",
            department="product",
            role="lead",
            capabilities=["产品战略", " roadmap规划", "团队管理", "跨部门协作"]
        )


class MarketingDepartment:
    """市场部"""
    
    @staticmethod
    def get_agents() -> list[DepartmentAgent]:
        return [
            DepartmentAgent(
                id="mkt_content",
                name="内容运营",
                department="marketing",
                role="agent",
                capabilities=["文案撰写", "内容策划", "社交媒体", "SEO"]
            ),
            DepartmentAgent(
                id="mkt_growth",
                name="增长运营",
                department="marketing",
                role="agent",
                capabilities=["用户增长", "活动策划", "数据分析", "A/B测试"]
            ),
        ]
    
    @staticmethod
    def get_lead() -> DepartmentAgent:
        return DepartmentAgent(
            id="mkt_lead",
            name="市场总监",
            department="marketing",
            role="lead",
            capabilities=["市场策略", "品牌推广", "渠道管理", "预算控制"]
        )


class OperationsDepartment:
    """运营部"""
    
    @staticmethod
    def get_agents() -> list[DepartmentAgent]:
        return [
            DepartmentAgent(
                id="ops_cs",
                name="客服",
                department="operations",
                role="agent",
                capabilities=["客户支持", "问题处理", "投诉解决", "满意度调研"]
            ),
            DepartmentAgent(
                id="ops_hr",
                name="HR",
                department="operations",
                role="agent",
                capabilities=["招聘", "培训", "绩效考核", "员工关系"]
            ),
        ]
    
    @staticmethod
    def get_lead() -> DepartmentAgent:
        return DepartmentAgent(
            id="ops_lead",
            name="运营总监",
            department="operations",
            role="lead",
            capabilities=["运营管理", "流程优化", "成本控制", "团队建设"]
        )


class DepartmentManager:
    """
    部门管理器
    
    管理所有部门及其 Agent。
    
    使用方式：
    ```python
    manager = DepartmentManager()
    
    # 获取所有部门
    departments = manager.list_departments()
    
    # 获取部门成员
    members = manager.get_department_members("engineering")
    
    # 查找适合的 Agent
    agent = manager.find_agent_for_task("需要设计 React 前端")
    ```
    """
    
    def __init__(self):
        self.departments = {
            "engineering": EngineeringDepartment,
            "design": DesignDepartment,
            "product": ProductDepartment,
            "marketing": MarketingDepartment,
            "operations": OperationsDepartment,
        }
        
        # 构建所有 Agent 索引
        self._all_agents: dict[str, DepartmentAgent] = {}
        self._build_index()
    
    def _build_index(self) -> None:
        """构建 Agent 索引"""
        for dept_name, dept_class in self.departments.items():
            # 添加 Lead
            lead = dept_class.get_lead()
            self._all_agents[lead.id] = lead
            
            # 添加 Agents
            for agent in dept_class.get_agents():
                self._all_agents[agent.id] = agent
    
    def list_departments(self) -> list[dict]:
        """列出所有部门"""
        return [
            {
                "id": name,
                "name": name.capitalize(),
                "member_count": len(cls.get_agents()) + 1,  # +1 for lead
                "capabilities": [c for a in cls.get_agents() for c in a.capabilities][:5]
            }
            for name, cls in self.departments.items()
        ]
    
    def get_department_lead(self, department: str) -> DepartmentAgent | None:
        """获取部门领导"""
        dept_class = self.departments.get(department)
        if dept_class:
            return dept_class.get_lead()
        return None
    
    def get_department_members(self, department: str) -> list[DepartmentAgent]:
        """获取部门所有成员（包括 Lead）"""
        dept_class = self.departments.get(department)
        if not dept_class:
            return []
        
        members = [dept_class.get_lead()]
        members.extend(dept_class.get_agents())
        
        return members
    
    def get_all_agents(self) -> list[DepartmentAgent]:
        """获取所有 Agent"""
        return list(self._all_agents.values())
    
    def get_agent(self, agent_id: str) -> DepartmentAgent | None:
        """获取特定 Agent"""
        return self._all_agents.get(agent_id)
    
    def find_agent_for_task(
        self,
        task_description: str,
        department: str | None = None
    ) -> DepartmentAgent | None:
        """
        为任务找到最适合的 Agent
        
        Args:
            task_description: 任务描述
            department: 可选的部门限制
            
        Returns:
            DepartmentAgent 或 None
        """
        task_lower = task_description.lower()
        
        candidates = []
        
        # 收集候选
        if department:
            members = self.get_department_members(department)
        else:
            members = self.get_all_agents()
        
        for agent in members:
            # 计算匹配度
            score = 0.0
            
            for cap in agent.capabilities:
                if cap.lower() in task_lower:
                    score += 1.0
            
            # 可用性加成
            if agent.status == "available":
                score += 0.5
            
            if score > 0:
                candidates.append((agent, score))
        
        if candidates:
            # 按分数排序
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]
        
        return None
    
    def assign_task(
        self,
        agent_id: str,
        task_description: str
    ) -> bool:
        """分配任务"""
        agent = self.get_agent(agent_id)
        if agent:
            agent.current_task = task_description
            agent.status = "busy"
            return True
        return False
    
    def complete_task(self, agent_id: str) -> bool:
        """完成任务"""
        agent = self.get_agent(agent_id)
        if agent:
            agent.current_task = None
            agent.status = "available"
            return True
        return False
    
    def get_department_status(self, department: str) -> dict:
        """获取部门状态"""
        members = self.get_department_members(department)
        
        available = sum(1 for m in members if m.status == "available")
        busy = sum(1 for m in members if m.status == "busy")
        
        return {
            "department": department,
            "total_members": len(members),
            "available": available,
            "busy": busy,
            "utilization": (busy / len(members)) if members else 0,
        }
    
    def get_all_status(self) -> dict:
        """获取所有部门状态"""
        return {
            dept: self.get_department_status(dept)
            for dept in self.departments.keys()
        }
    
    def __repr__(self) -> str:
        agent_count = len(self._all_agents)
        return f"DepartmentManager(agents={agent_count})"
