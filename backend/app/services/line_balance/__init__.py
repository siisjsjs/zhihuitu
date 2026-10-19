"""产线平衡优化算法包（纯标准库，无 GUI / 无授权依赖）。

复用自扩展计划书 §3-§5。对外主入口：optimize_line。
"""
from .api import optimize_line, derive_kpi
from .optimizer import optimize_with_backtracking, StableOptimizer, evaluate_solution

__all__ = [
    "optimize_line",
    "derive_kpi",
    "optimize_with_backtracking",
    "StableOptimizer",
    "evaluate_solution",
]
