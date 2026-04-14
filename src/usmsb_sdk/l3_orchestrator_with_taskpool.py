# -*- coding: utf-8 -*-
"""
L3OrchestratorWithTaskPool - 带真实任务源的 L3 编排器

集成 TaskPool，让 Agent 可以自动认领和完成任务：
1. 从任务池获取任务
2. 执行任务
3. 获得 VIBE 奖励
4. 触发价值循环

使用方式：
    orch = L3OrchestratorWithTaskPool(
        agent_id="agent_001",
        wallet_address="0x...",
    )
    
    # 自动执行任务
    orch.run_autonomous_cycle()
    
    # 或手动控制
    task = orch.claim_task()
    orch.execute_task(task)
"""

from typing import Any

from usmsb_sdk.l3_orchestrator_with_real_vibe import L3OrchestratorWithRealVIBE
from usmsb_sdk.services.task_pool import TaskPool, Task, TaskStatus


class L3OrchestratorWithTaskPool(L3OrchestratorWithRealVIBE):
    """
    带真实任务源的 L3 编排器
    
    在 L3OrchestratorWithRealVIBE 基础上增加：
    - TaskPool 集成
    - 自动任务认领
    - 任务执行和奖励
    - 任务驱动的价值循环
    """
    
    def __init__(
        self,
        agent_id: str,
        wallet_address: str,
        services: dict | None = None,
        llm_adapter=None,
        task_pool: TaskPool | None = None,
    ):
        """
        初始化
        
        Args:
            agent_id: Agent ID
            wallet_address: 钱包地址
            services: L4 服务
            llm_adapter: LLM 适配器
            task_pool: 任务池（可选）
        """
        # 初始化父类
        super().__init__(agent_id, wallet_address, services, llm_adapter)
        
        # 初始化任务池
        self.task_pool = task_pool or TaskPool()
        
        # 任务历史
        self._completed_tasks: list[str] = []
        self._total_rewards = 0.0
    
    def claim_task(self) -> Task | None:
        """
        从任务池认领任务
        
        根据 Agent 的能力匹配最合适的任务。
        
        Returns:
            Task 或 None（没有合适的任务）
        """
        # 获取能力画像
        profile = self.get_capability_profile()
        capabilities = list(profile["capabilities"].keys())
        
        if not capabilities:
            capabilities = ["general"]
        
        # 从任务池认领
        task = self.task_pool.claim_task(
            agent_id=self.agent_id,
            capabilities=capabilities
        )
        
        if task:
            print(f"[L3OrchestratorWithTaskPool] Claimed task: {task.title}")
            
            # 更新 Agent 状态
            self.add_capability_experience(
                capability=task.task_type,
                xp=int(task.reward / 10),
                quality=0.5,
                event_type="task_claimed"
            )
        
        return task
    
    def execute_task(self, task: Task) -> dict:
        """
        执行任务
        
        模拟任务执行（实际应该调用 LLM 或外部服务）。
        
        Args:
            task: 任务对象
            
        Returns:
            dict: 执行结果
        """
        import random
        import time
        
        # 开始任务
        self.task_pool.start_task(task.id)
        
        # 模拟执行（实际这里应该调用 LLM 或外部服务）
        start_time = time.time()
        
        # 模拟任务执行
        # 真实场景：调用 LLM 执行任务
        success = random.random() > 0.2  # 80% 成功率
        quality_score = random.uniform(0.6, 1.0) if success else random.uniform(0.1, 0.4)
        
        completion_time = time.time() - start_time
        
        # 完成任务
        reward = self.task_pool.complete_task(
            task_id=task.id,
            success=success,
            quality_score=quality_score,
            completion_time=completion_time,
            result_data={
                "task_type": task.task_type,
                "quality": quality_score
            }
        )
        
        # 获得 VIBE 奖励
        if success:
            # 直接收款（简化处理）
            self._total_rewards += reward
            print(f"[L3OrchestratorWithTaskPool] Task completed! Reward: {reward:.2f} VIBE")
        
        # 评估适应度
        self.evaluate_fitness({
            "total_value": self._total_rewards,
            "total_cost": task.reward * 0.5,  # 假设成本是奖励的一半
            "total_tasks": len(self._completed_tasks) + 1,
            "succeeded_tasks": len([t for t in self._completed_tasks if t]) + (1 if success else 0),
        })
        
        # 记录能力经验
        self.add_capability_experience(
            capability=task.task_type,
            xp=int(task.reward / 5) if success else int(task.reward / 10),
            quality=quality_score,
            event_type="task_completed" if success else "task_failed"
        )
        
        # 记录已完成任务
        self._completed_tasks.append(task.id)
        
        return {
            "success": success,
            "task_id": task.id,
            "reward": reward,
            "quality_score": quality_score,
            "completion_time": completion_time,
        }
    
    def run_autonomous_cycle(self, max_tasks: int = 3) -> dict:
        """
        运行自主周期
        
        Agent 自动：
        1. 认领任务
        2. 执行任务
        3. 获得奖励
        4. 触发价值循环
        
        Args:
            max_tasks: 最大任务数
            
        Returns:
            dict: 周期结果
        """
        results = {
            "tasks_claimed": 0,
            "tasks_completed": 0,
            "total_reward": 0.0,
            "fitness_score": None,
        }
        
        # 执行多个任务
        for _ in range(max_tasks):
            # 认领任务
            task = self.claim_task()
            
            if not task:
                break  # 没有可用任务
            
            results["tasks_claimed"] += 1
            
            # 执行任务
            exec_result = self.execute_task(task)
            
            if exec_result["success"]:
                results["tasks_completed"] += 1
                results["total_reward"] += exec_result["reward"]
        
        # 获取当前适应度
        if self.agent_state.fitness_score:
            results["fitness_score"] = self.agent_state.fitness_score.overall_score
        
        # 检查是否可以复制
        can_replicate, reason = self.check_can_replicate()
        results["can_replicate"] = can_replicate
        results["replication_blocked_reason"] = reason if not can_replicate else None
        
        return results
    
    def get_task_statistics(self) -> dict:
        """获取任务统计"""
        stats = self.task_pool.get_statistics()
        agent_tasks = self.task_pool.get_agent_tasks(self.agent_id)
        
        return {
            "pool_stats": stats,
            "my_tasks": len(agent_tasks),
            "my_completed": len(self._completed_tasks),
            "my_total_rewards": self._total_rewards,
            "my_pending": len([t for t in agent_tasks if t.status == "in_progress"]),
        }
    
    def seed_tasks(self, count: int = 20) -> int:
        """
        填充演示任务
        
        Returns:
            int: 添加的任务数
        """
        return self.task_pool.seed_demo_tasks(count)
    
    def get_agent_status(self) -> dict:
        """获取完整 Agent 状态（增强版）"""
        status = super().get_agent_status()
        
        # 添加任务相关状态
        status["tasks"] = {
            "completed": len(self._completed_tasks),
            "total_rewards": self._total_rewards,
        }
        
        return status
    
    def __repr__(self) -> str:
        return f"L3OrchestratorWithTaskPool(agent={self.agent_id}, tasks={len(self._completed_tasks)}, rewards={self._total_rewards:.2f})"
