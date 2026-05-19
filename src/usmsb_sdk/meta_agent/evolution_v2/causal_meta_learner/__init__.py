"""
因果元学习器

CausalMetaLearner - MAML + EWC 完整实现

子模块：
- meta_learner.py: 主类
- ewc_penalty.py: EWC 防止灾难性遗忘
- task_sampler.py: 因果任务采样器
"""

from .meta_learner import CausalMetaLearner, CausalMetaLearnerConfig, MetaLearningResult
from .ewc_penalty import EWCPenalty, OnlineEWC, EmpiricalFisher
from .task_sampler import CausalTaskSampler, CausalTask, MetaBatchSampler, AdaptiveTaskSampler

__all__ = [
    "CausalMetaLearner",
    "CausalMetaLearnerConfig",
    "MetaLearningResult",
    "EWCPenalty",
    "OnlineEWC",
    "EmpiricalFisher",
    "CausalTaskSampler",
    "CausalTask",
    "MetaBatchSampler",
    "AdaptiveTaskSampler",
]
