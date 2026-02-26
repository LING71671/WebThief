"""
降级克隆策略模块

提供网站克隆的智能策略选择和降级处理能力。
"""

from .clone_strategy import (
    CloneStrategy,
    StrategySelector,
    StrategyResult,
    LimitationType,
    LimitationRecord,
    LimitationsWriter,
)

__all__ = [
    "CloneStrategy",
    "StrategySelector",
    "StrategyResult",
    "LimitationType",
    "LimitationRecord",
    "LimitationsWriter",
]
