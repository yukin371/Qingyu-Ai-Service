"""
Authentication Middleware - 认证中间件

提供 Agent 请求的认证和授权功能。
"""

import logging
from typing import Awaitable, Callable, Dict, List, Optional, Set

from src.agent_runtime.orchestration.middleware.base import (
    AgentMiddleware,
    MiddlewareResult,
)
from src.common.types.agent_types import AgentContext


logger = logging.getLogger(__name__)


class AuthMiddleware(AgentMiddleware):
    """
    认证中间件

    验证请求是否经过认证和授权。

    Attributes:
        authenticated_users: 已认证的用户 ID 集合
        permissions: 用户权限映射 (user_id -> set of permissions)
        require_auth: 是否要求认证
    """

    def __init__(
        self,
        authenticated_users: Optional[Set[str]] = None,
        permissions: Optional[Dict[str, Set[str]]] = None,
        require_auth: bool = True,
    ):
        """
        初始化认证中间件

        Args:
            authenticated_users: 已认证的用户集合
            permissions: 用户权限映射
            require_auth: 是否要求认证
        """
        super().__init__(name="auth", order=10)
        self.authenticated_users = authenticated_users or set()
        self.permissions = permissions or {}
        self.require_auth = require_auth

    async def process(
        self,
        context: AgentContext,
        next_call: Callable[[], Awaitable[MiddlewareResult]],
    ) -> MiddlewareResult:
        """
        处理认证检查

        Args:
            context: Agent 上下文
            next_call: 下一个中间件或处理器

        Returns:
            MiddlewareResult 处理结果
        """
        # 检查用户是否已认证
        if not self._is_authenticated(context.user_id):
            if self.require_auth:
                logger.warning(f"Unauthorized access attempt: user={context.user_id}")
                return MiddlewareResult(
                    success=False,
                    error="Authentication required",
                )
            else:
                # 不要求认证，继续处理
                logger.debug(f"Allowing unauthenticated access: user={context.user_id}")
                return await next_call()

        # 检查权限（如果配置了）
        required_permissions = context.metadata.get("required_permissions")
        if required_permissions:
            if not self._has_permissions(context.user_id, required_permissions):
                logger.warning(
                    f"Permission denied: user={context.user_id}, "
                    f"required={required_permissions}"
                )
                return MiddlewareResult(
                    success=False,
                    error="Permission denied",
                )

        logger.info(f"Authentication successful: user={context.user_id}")
        return await next_call()

    def _is_authenticated(self, user_id: str) -> bool:
        """检查用户是否已认证"""
        return user_id in self.authenticated_users

    def _has_permissions(self, user_id: str, permissions: List[str]) -> bool:
        """检查用户是否拥有所需权限"""
        user_permissions = self.permissions.get(user_id, set())
        return all(perm in user_permissions for perm in permissions)

    def add_user(self, user_id: str, permissions: Optional[List[str]] = None) -> None:
        """
        添加已认证用户

        Args:
            user_id: 用户 ID
            permissions: 用户权限列表
        """
        self.authenticated_users.add(user_id)
        if permissions:
            self.permissions[user_id] = set(permissions)
        logger.info(f"Added authenticated user: {user_id}")

    def remove_user(self, user_id: str) -> None:
        """
        移除认证用户

        Args:
            user_id: 用户 ID
        """
        self.authenticated_users.discard(user_id)
        self.permissions.pop(user_id, None)
        logger.info(f"Removed authenticated user: {user_id}")
