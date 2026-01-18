# 认证与授权

本文档介绍 Qingyu Backend AI 的认证和授权机制。

## 概述

### 认证 vs 授权

- **认证 (Authentication)**: 验证用户身份
- **授权 (Authorization)**: 验证用户权限

```
┌─────────────────────────────────────────────────┐
│                    用户                           │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│              认证层 (AuthN)                      │
│  - 验证凭证                                      │
│  - 确立身份                                      │
│  - 创建会话                                      │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│              授权层 (AuthZ)                      │
│  - 检查权限                                      │
│  - 验证访问控制                                  │
│  - 强制策略                                      │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│               资源访问                           │
└─────────────────────────────────────────────────┘
```

## 认证机制

### 1. Token 认证

```python
import jwt
from datetime import datetime, timedelta
from typing import Optional

class TokenAuthenticator:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def generate_token(
        self,
        user_id: str,
        expires_in: int = 3600,
        additional_claims: dict = None,
    ) -> str:
        """生成访问令牌"""
        now = datetime.utcnow()

        payload = {
            "user_id": user_id,
            "iat": now,
            "exp": now + timedelta(seconds=expires_in),
            "type": "access",
        }

        if additional_claims:
            payload.update(additional_claims)

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        return token

    def verify_token(self, token: str) -> Optional[dict]:
        """验证令牌"""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )

            # 检查令牌类型
            if payload.get("type") != "access":
                return None

            return payload

        except jwt.ExpiredSignatureError:
            # 令牌已过期
            return None
        except jwt.InvalidTokenError:
            # 无效令牌
            return None

    def refresh_token(self, old_token: str) -> Optional[str]:
        """刷新令牌"""
        payload = self.verify_token(old_token)

        if not payload:
            return None

        # 生成新令牌
        user_id = payload["user_id"]
        return self.generate_token(user_id)
```

### 2. API Key 认证

```python
import hashlib
import secrets
from typing import Optional

class APIKeyAuthenticator:
    def __init__(self):
        self.api_keys = {}  # 实际应该使用数据库

    def generate_api_key(self, user_id: str, name: str = "default") -> tuple[str, str]:
        """生成 API 密钥"""
        # 生成随机密钥
        key_id = secrets.token_hex(16)
        key_secret = secrets.token_urlsafe(32)

        # 组合
        api_key = f"qyk_{key_id}_{key_secret}"

        # 存储（实际应该存储哈希值）
        self.api_keys[key_id] = {
            "user_id": user_id,
            "name": name,
            "key_hash": self._hash_key(key_secret),
            "created_at": datetime.now(),
            "active": True,
        }

        return api_key, key_id

    def _hash_key(self, key_secret: str) -> str:
        """哈希密钥"""
        return hashlib.sha256(key_secret.encode()).hexdigest()

    def verify_api_key(self, api_key: str) -> Optional[dict]:
        """验证 API 密钥"""
        try:
            # 解析密钥
            prefix, key_id, key_secret = api_key.split("_", 2)

            if prefix != "qyk":
                return None

            # 查找密钥
            key_data = self.api_keys.get(key_id)

            if not key_data:
                return None

            # 验证哈希
            key_hash = self._hash_key(key_secret)

            if key_hash != key_data["key_hash"]:
                return None

            # 检查状态
            if not key_data["active"]:
                return None

            return {
                "user_id": key_data["user_id"],
                "key_id": key_id,
                "key_name": key_data["name"],
            }

        except (ValueError, AttributeError):
            return None

    def revoke_api_key(self, key_id: str) -> bool:
        """撤销 API 密钥"""
        if key_id in self.api_keys:
            self.api_keys[key_id]["active"] = False
            return True

        return False
```

### 3. 会话认证

```python
from src.agent_runtime.session_manager import SessionManager

class SessionAuthenticator:
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager

    async def authenticate_session(
        self,
        session_id: str,
        user_id: str,
    ) -> bool:
        """验证会话"""
        # 获取会话
        session = await self.session_manager.get_session(session_id)

        if not session:
            return False

        # 验证用户
        if session.user_id != user_id:
            return False

        # 检查过期
        if session.expires_at < datetime.now():
            return False

        return True

    async def create_auth_session(
        self,
        user_id: str,
        agent_id: str,
        ttl: int = 3600,
    ) -> str:
        """创建认证会话"""
        session = await self.session_manager.create_session(
            user_id=user_id,
            agent_id=agent_id,
        )

        return session.session_id
```

## 授权机制

### 1. 基于角色的访问控制 (RBAC)

```python
from enum import Enum
from typing import List, Set

class Role(Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"
    PREMIUM = "premium"

class Permission(Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    MANAGE = "manage"
    EXECUTE_AGENT = "execute_agent"

class RBACAuthorizer:
    def __init__(self):
        # 角色权限映射
        self.role_permissions = {
            Role.ADMIN: {
                Permission.READ,
                Permission.WRITE,
                Permission.DELETE,
                Permission.MANAGE,
                Permission.EXECUTE_AGENT,
            },
            Role.PREMIUM: {
                Permission.READ,
                Permission.WRITE,
                Permission.EXECUTE_AGENT,
            },
            Role.USER: {
                Permission.READ,
                Permission.EXECUTE_AGENT,
            },
            Role.GUEST: {
                Permission.READ,
            },
        }

    def get_permissions(self, role: Role) -> Set[Permission]:
        """获取角色的所有权限"""
        return self.role_permissions.get(role, set())

    def has_permission(
        self,
        role: Role,
        permission: Permission,
    ) -> bool:
        """检查角色是否有权限"""
        return permission in self.get_permissions(role)

    def require_permission(
        self,
        required_permissions: List[Permission],
    ):
        """装饰器：要求特定权限"""
        def decorator(func):
            async def wrapper(context: AgentContext, *args, **kwargs):
                # 获取用户角色
                user_role = await self._get_user_role(context.user_id)

                # 检查权限
                for permission in required_permissions:
                    if not self.has_permission(user_role, permission):
                        raise PermissionError(
                            f"Permission {permission} required"
                        )

                # 执行函数
                return await func(context, *args, **kwargs)

            return wrapper
        return decorator

    async def _get_user_role(self, user_id: str) -> Role:
        """获取用户角色（实际应该查询数据库）"""
        # 简化实现
        return Role.USER
```

### 2. 基于资源的访问控制

```python
class ResourceAuthorizer:
    def __init__(self):
        # 资源所有权
        self.resource_owners = {}  # resource_id -> user_id
        # 资源权限
        self.resource_permissions = {}  # resource_id -> {user_id -> permissions}

    def grant_access(
        self,
        resource_id: str,
        user_id: str,
        permissions: List[str],
    ):
        """授予用户对资源的访问权限"""
        if resource_id not in self.resource_permissions:
            self.resource_permissions[resource_id] = {}

        self.resource_permissions[resource_id][user_id] = set(permissions)

    async def check_access(
        self,
        resource_id: str,
        user_id: str,
        required_permission: str,
    ) -> bool:
        """检查用户对资源的访问权限"""

        # 检查是否是所有者
        if self.resource_owners.get(resource_id) == user_id:
            return True

        # 检查显式权限
        resource_perms = self.resource_permissions.get(resource_id, {})
        user_perms = resource_perms.get(user_id, set())

        if required_permission in user_perms:
            return True

        return False

    async def require_access(
        self,
        resource_id: str,
        required_permission: str,
    ):
        """装饰器：要求对资源的访问权限"""
        def decorator(func):
            async def wrapper(context: AgentContext, *args, **kwargs):
                user_id = context.user_id

                if not await self.check_access(
                    resource_id,
                    user_id,
                    required_permission,
                ):
                    raise PermissionError(
                        f"No {required_permission} permission for resource {resource_id}"
                    )

                return await func(context, *args, **kwargs)

            return wrapper
        return decorator
```

### 3. 速率限制

```python
import time
from collections import defaultdict
from typing import Dict

class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)

    async def check_rate_limit(
        self,
        user_id: str,
        max_requests: int = 100,
        window_seconds: int = 60,
    ) -> tuple[bool, dict]:
        """
        检查速率限制
        返回: (allowed, info)
        """
        now = time.time()
        window_start = now - window_seconds

        # 清理旧请求
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if req_time > window_start
        ]

        # 检查限制
        request_count = len(self.requests[user_id])

        if request_count >= max_requests:
            # 计算重置时间
            oldest_request = min(self.requests[user_id])
            reset_time = oldest_request + window_seconds

            return False, {
                "limit": max_requests,
                "remaining": 0,
                "reset": int(reset_time),
            }

        # 记录请求
        self.requests[user_id].append(now)

        return True, {
            "limit": max_requests,
            "remaining": max_requests - request_count - 1,
            "reset": int(now + window_seconds),
        }

    async def require_rate_limit(
        self,
        max_requests: int = 100,
        window_seconds: int = 60,
    ):
        """装饰器：应用速率限制"""
        def decorator(func):
            async def wrapper(context: AgentContext, *args, **kwargs):
                user_id = context.user_id

                allowed, info = await self.check_rate_limit(
                    user_id,
                    max_requests,
                    window_seconds,
                )

                if not allowed:
                    raise RateLimitError(
                        f"Rate limit exceeded. Try again in {info['reset']} seconds"
                    )

                return await func(context, *args, **kwargs)

            return wrapper
        return decorator
```

## 中间件实现

### 认证中间件

```python
from src.middleware.base import BaseMiddleware

class AuthenticationMiddleware(BaseMiddleware):
    def __init__(
        self,
        name: str,
        token_authenticator: TokenAuthenticator,
        api_key_authenticator: APIKeyAuthenticator,
        session_authenticator: SessionAuthenticator,
    ):
        super().__init__(name)
        self.token_auth = token_authenticator
        self.api_key_auth = api_key_authenticator
        self.session_auth = session_authenticator

    async def process(self, context: AgentContext) -> MiddlewareResult:
        """认证用户"""

        # 检查认证信息
        auth_result = await self._authenticate(context)

        if not auth_result.success:
            return MiddlewareResult(
                success=False,
                agent_result=AgentResult(
                    success=False,
                    output="",
                    error=auth_result.error,
                ),
                skip_rest=True,
            )

        # 添加认证信息到上下文
        context.metadata["auth"] = auth_result.data

        # 继续处理
        return await self.call_next(context)

    async def _authenticate(self, context: AgentContext) -> AuthResult:
        """尝试多种认证方式"""

        # 1. Token 认证
        token = context.metadata.get("auth_token")
        if token:
            payload = self.token_auth.verify_token(token)
            if payload:
                return AuthResult(
                    success=True,
                    data={"user_id": payload["user_id"], "auth_method": "token"},
                )

        # 2. API Key 认证
        api_key = context.metadata.get("api_key")
        if api_key:
            key_data = self.api_key_auth.verify_api_key(api_key)
            if key_data:
                return AuthResult(
                    success=True,
                    data={
                        "user_id": key_data["user_id"],
                        "auth_method": "api_key",
                        "key_id": key_data["key_id"],
                    },
                )

        # 3. 会话认证
        session_id = context.session_id
        user_id = context.user_id
        if session_id and user_id:
            valid = await self.session_auth.authenticate_session(
                session_id,
                user_id,
            )
            if valid:
                return AuthResult(
                    success=True,
                    data={"user_id": user_id, "auth_method": "session"},
                )

        # 所有认证都失败
        return AuthResult(
            success=False,
            error="Authentication required",
        )
```

### 授权中间件

```python
class AuthorizationMiddleware(BaseMiddleware):
    def __init__(
        self,
        name: str,
        authorizer: RBACAuthorizer,
    ):
        super().__init__(name)
        self.authorizer = authorizer

    async def process(self, context: AgentContext) -> MiddlewareResult:
        """检查权限"""

        # 获取认证信息
        auth_info = context.metadata.get("auth")
        if not auth_info:
            return MiddlewareResult(
                success=False,
                agent_result=AgentResult(
                    success=False,
                    error="Not authenticated",
                ),
                skip_rest=True,
            )

        # 获取用户角色
        user_role = await self.authorizer._get_user_role(
            auth_info["user_id"]
        )

        # 检查执行 Agent 的权限
        if not self.authorizer.has_permission(
            user_role,
            Permission.EXECUTE_AGENT,
        ):
            return MiddlewareResult(
                success=False,
                agent_result=AgentResult(
                    success=False,
                    error="Insufficient permissions to execute agent",
                ),
                skip_rest=True,
            )

        # 继续处理
        return await self.call_next(context)
```

### 速率限制中间件

```python
class RateLimitMiddleware(BaseMiddleware):
    def __init__(
        self,
        name: str,
        rate_limiter: RateLimiter,
        max_requests: int = 100,
        window_seconds: int = 60,
    ):
        super().__init__(name)
        self.rate_limiter = rate_limiter
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def process(self, context: AgentContext) -> MiddlewareResult:
        """应用速率限制"""

        # 获取用户 ID
        user_id = context.metadata.get("auth", {}).get("user_id")
        if not user_id:
            return MiddlewareResult(
                success=False,
                agent_result=AgentResult(
                    success=False,
                    error="Authentication required for rate limiting",
                ),
                skip_rest=True,
            )

        # 检查速率限制
        allowed, info = await self.rate_limiter.check_rate_limit(
            user_id,
            self.max_requests,
            self.window_seconds,
        )

        if not allowed:
            return MiddlewareResult(
                success=False,
                agent_result=AgentResult(
                    success=False,
                    error=f"Rate limit exceeded. Try again in {info['reset']} seconds",
                    metadata={"rate_limit_info": info},
                ),
                skip_rest=True,
            )

        # 添加速率限制信息到响应
        context.metadata["rate_limit"] = info

        # 继续处理
        return await self.call_next(context)
```

## 使用示例

### 完整的认证授权流程

```python
# 初始化
token_auth = TokenAuthenticator(secret_key="your-secret-key")
api_key_auth = APIKeyAuthenticator()
session_auth = SessionAuthenticator(session_manager)
authorizer = RBACAuthorizer()
rate_limiter = RateLimiter()

# 创建中间件管道
pipeline = MiddlewarePipeline()

# 1. 认证
pipeline.add(AuthenticationMiddleware(
    name="auth",
    token_authenticator=token_auth,
    api_key_authenticator=api_key_auth,
    session_authenticator=session_auth,
))

# 2. 授权
pipeline.add(AuthorizationMiddleware(
    name="authorization",
    authorizer=authorizer,
))

# 3. 速率限制
pipeline.add(RateLimitMiddleware(
    name="rate_limit",
    rate_limiter=rate_limiter,
    max_requests=100,
    window_seconds=60,
))

# 应用到执行器
executor.set_middleware_pipeline(pipeline)
```

### 生成和使用 Token

```python
# 1. 用户登录后生成 Token
authenticator = TokenAuthenticator(secret_key="your-secret-key")
token = authenticator.generate_token(
    user_id="user_123",
    expires_in=3600,  # 1小时
)

print(f"Token: {token}")

# 2. 客户端使用 Token
context = AgentContext(
    agent_id="chatbot",
    user_id="user_123",
    session_id="sess_abc",
    current_task="Hello",
    metadata={
        "auth_token": token,  # 包含 Token
    },
)

result = await executor.execute(context)
```

### 生成和使用 API Key

```python
# 1. 为用户生成 API Key
api_key_auth = APIKeyAuthenticator()
api_key, key_id = api_key_auth.generate_api_key(
    user_id="user_123",
    name="My App",
)

print(f"API Key: {api_key}")

# 2. 应用使用 API Key
context = AgentContext(
    agent_id="chatbot",
    user_id="user_123",  # 可以从 API Key 推断
    session_id="sess_abc",
    current_task="Hello",
    metadata={
        "api_key": api_key,  # 包含 API Key
    },
)

result = await executor.execute(context)
```

## 最佳实践

### 1. 使用安全的密钥存储

```python
import os
from cryptography.fernet import Fernet

class SecureKeyStorage:
    def __init__(self):
        # 从环境变量获取加密密钥
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            raise ValueError("ENCRYPTION_KEY not set")

        self.cipher = Fernet(key.encode())

    def encrypt(self, data: str) -> str:
        """加密数据"""
        encrypted = self.cipher.encrypt(data.encode())
        return encrypted.decode()

    def decrypt(self, encrypted_data: str) -> str:
        """解密数据"""
        decrypted = self.cipher.decrypt(encrypted_data.encode())
        return decrypted.decode()
```

### 2. 实现令牌刷新

```python
class RefreshTokenManager:
    def __init__(self, authenticator: TokenAuthenticator):
        self.authenticator = authenticator

    async def refresh_if_needed(self, token: str) -> str:
        """如果需要，刷新令牌"""
        try:
            # 解码令牌（不验证过期）
            payload = jwt.decode(
                token,
                options={"verify_signature": False},
            )

            # 检查是否即将过期（5分钟内）
            exp = payload["exp"]
            now = time.time()

            if exp - now < 300:  # 5分钟
                # 刷新令牌
                user_id = payload["user_id"]
                return self.authenticator.generate_token(user_id)

            return token

        except Exception:
            return token
```

### 3. 记录认证事件

```python
class AuthEventLogger:
    async def log_authentication(
        self,
        user_id: str,
        method: str,
        success: bool,
        details: dict = None,
    ):
        """记录认证事件"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "method": method,
            "success": success,
            "details": details or {},
        }

        # 写入审计日志
        await self.audit_logger.log(event)

        # 如果失败，发送告警
        if not success:
            await self.alert_sender.send_alert(
                f"Authentication failed for user {user_id}",
                event,
            )
```

## 相关文档

- [安全概述](overview.md) - 整体安全架构
- [提示词注入防护](prompt-injection.md) - 输入安全
- [输出清洗](output-sanitization.md) - 输出安全
- [数据保护](data-protection.md) - 敏感数据保护
