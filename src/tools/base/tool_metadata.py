"""
工具元数据定义
"""
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ToolCategory(str, Enum):
    """工具类别"""

    KNOWLEDGE = "knowledge"  # 知识检索工具
    CREATION = "creation"  # 内容创作工具
    ANALYSIS = "analysis"  # 分析工具
    MANAGEMENT = "management"  # 项目管理工具
    EXTERNAL = "external"  # 外部服务工具
    SYSTEM = "system"  # 系统工具


class ToolMetadata(BaseModel):
    """工具元数据

    MCP（Modular, Composable, Portable）工具范式的元数据定义
    """

    # 基础信息
    name: str = Field(..., description="工具名称（唯一标识符）")
    display_name: Optional[str] = Field(None, description="显示名称")
    description: str = Field(..., description="工具描述")
    version: str = Field(default="1.0.0", description="工具版本")

    # 分类和标签
    category: ToolCategory = Field(..., description="工具类别")
    tags: List[str] = Field(default_factory=list, description="工具标签")

    # 权限和要求
    requires_auth: bool = Field(default=False, description="是否需要身份认证")
    requires_project: bool = Field(default=False, description="是否需要项目上下文")
    requires_user_approval: bool = Field(default=False, description="是否需要用户批准")

    # 性能和资源
    estimated_tokens: Optional[int] = Field(None, description="预估Token消耗")
    estimated_duration: Optional[float] = Field(None, description="预估执行时间（秒）")
    max_retries: int = Field(default=3, description="最大重试次数")
    timeout: Optional[float] = Field(None, description="超时时间（秒）")

    # 扩展信息
    examples: List[Dict] = Field(default_factory=list, description="使用示例")
    limitations: List[str] = Field(default_factory=list, description="限制说明")
    metadata_extra: Dict = Field(default_factory=dict, description="额外元数据")

    def __str__(self) -> str:
        return f"Tool<{self.name} v{self.version} ({self.category})>"

    def __repr__(self) -> str:
        return self.__str__()

