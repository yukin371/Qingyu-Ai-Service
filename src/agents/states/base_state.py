"""Agent基础状态定义"""

import operator
from typing import Annotated, Any, Dict, List

from typing_extensions import TypedDict


def merge_dict_values(current: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """合并字典值（自定义Reducer）

    Args:
        current: 当前字典
        new: 新字典

    Returns:
        合并后的字典
    """
    result = current.copy()
    result.update(new)
    return result


class BaseAgentState(TypedDict, total=False):
    """Agent基础状态

    所有Agent状态的基类，提供通用字段
    """

    # ===== 输入 =====
    task: str  # 任务描述
    user_id: str  # 用户ID
    project_id: str  # 项目ID

    # ===== 工作流控制 =====
    current_step: str  # 当前步骤
    max_iterations: int  # 最大迭代次数
    iteration_count: int  # 当前迭代次数

    # ===== 错误处理 =====
    errors: Annotated[List[str], operator.add]  # 错误列表（自动累积）
    warnings: Annotated[List[str], operator.add]  # 警告列表（自动累积）

    # ===== 推理过程 =====
    reasoning: Annotated[List[str], operator.add]  # 推理步骤（自动累积）

    # ===== 元数据 =====
    metadata: Dict[str, Any]  # 元数据

