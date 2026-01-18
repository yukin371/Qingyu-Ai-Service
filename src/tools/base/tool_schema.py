"""
工具输入模式基类
"""
from pydantic import BaseModel, ConfigDict


class ToolInputSchema(BaseModel):
    """工具输入模式基类

    所有工具输入都应继承此类
    """

    model_config = ConfigDict(
        extra="forbid",  # 禁止额外字段
        validate_assignment=True,  # 验证赋值
        arbitrary_types_allowed=True,  # 允许任意类型
    )

