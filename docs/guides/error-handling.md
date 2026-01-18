# 错误处理指南

本指南介绍 Qingyu Backend AI 中的错误处理模式和最佳实践。

## 错误类型

### 系统错误分类

```
┌─────────────────────────────────────────────────────────┐
│                    错误层次                             │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │   应用层错误 (Application Errors)               │   │
│  │   - 业务逻辑错误                                 │   │
│  │   - 验证失败                                     │   │
│  │   - 权限错误                                     │   │
│  └──────────────┬───────────────────────────────────┘   │
│                 │                                       │
│  ┌──────────────▼───────────────────────────────────┐   │
│  │   Agent 执行错误 (Agent Execution Errors)       │   │
│  │   - LLM API 错误                                │   │
│  │   - 超时错误                                     │   │
│  │   - 资源限制                                     │   │
│  └──────────────┬───────────────────────────────────┘   │
│                 │                                       │
│  ┌──────────────▼───────────────────────────────────┐   │
│  │   中间件错误 (Middleware Errors)                │   │
│  │   - 认证失败                                     │   │
│  │   - 验证失败                                     │   │
│  │   - 速率限制                                     │   │
│  └──────────────┬───────────────────────────────────┘   │
│                 │                                       │
│  ┌──────────────▼───────────────────────────────────┐   │
│  │   系统错误 (System Errors)                      │   │
│  │   - 网络错误                                     │   │
│  │   - 数据库错误                                   │   │
│  │   - 配置错误                                     │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 标准错误类型

```python
from enum import Enum

class ErrorType(Enum):
    # 验证错误
    VALIDATION_ERROR = "validation_error"
    INVALID_INPUT = "invalid_input"
    MISSING_REQUIRED_FIELD = "missing_required_field"

    # 认证授权错误
    AUTHENTICATION_FAILED = "authentication_failed"
    AUTHORIZATION_FAILED = "authorization_failed"
    TOKEN_EXPIRED = "token_expired"
    SESSION_INVALID = "session_invalid"

    # Agent 执行错误
    AGENT_TIMEOUT = "agent_timeout"
    AGENT_FAILED = "agent_failed"
    LLM_API_ERROR = "llm_api_error"
    LLM_RATE_LIMITED = "llm_rate_limited"

    # 资源错误
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    QUOTA_EXCEEDED = "quota_exceeded"

    # 系统错误
    INTERNAL_ERROR = "internal_error"
    DATABASE_ERROR = "database_error"
    NETWORK_ERROR = "network_error"
    CONFIGURATION_ERROR = "configuration_error"
```

## 错误处理模式

### 1. AgentResult 错误模式

```python
from src.common.types.agent_types import AgentResult

# 执行失败时返回错误结果
error_result = AgentResult(
    success=False,
    output="",
    error="User input too long",
    metadata={
        "error_type": "validation_error",
        "error_code": "INPUT_TOO_LONG",
        "max_length": 10000,
        "actual_length": 15000,
    },
)
```

### 2. 中间件错误处理

```python
from src.middleware.base import BaseMiddleware

class ErrorHandlingMiddleware(BaseMiddleware):
    async def process(self, context: AgentContext) -> MiddlewareResult:
        """统一错误处理"""
        try:
            return await self.call_next(context)
        except ValueError as e:
            # 处理值错误
            return MiddlewareResult(
                success=False,
                agent_result=AgentResult(
                    success=False,
                    output="",
                    error=str(e),
                    metadata={"error_type": ErrorType.VALIDATION_ERROR.value},
                ),
            )
        except TimeoutError as e:
            # 处理超时
            return MiddlewareResult(
                success=False,
                agent_result=AgentResult(
                    success=False,
                    output="",
                    error="Request timed out",
                    metadata={"error_type": ErrorType.AGENT_TIMEOUT.value},
                ),
            )
        except Exception as e:
            # 处理未预期的错误
            return MiddlewareResult(
                success=False,
                agent_result=AgentResult(
                    success=False,
                    output="",
                    error="An unexpected error occurred",
                    metadata={"error_type": ErrorType.INTERNAL_ERROR.value},
                ),
            )
```

### 3. Executor 错误处理

```python
class SafeExecutor(AgentExecutor):
    async def execute(self, context: AgentContext) -> AgentResult:
        """带错误保护的执行"""
        try:
            # 尝试执行
            return await super().execute(context)
        except Exception as e:
            # 记录错误
            logger.error(f"Executor error: {e}", exc_info=True)

            # 返回错误结果
            return AgentResult(
                success=False,
                output="",
                error=f"Execution failed: {str(e)}",
                metadata={
                    "error_type": ErrorType.INTERNAL_ERROR.value,
                    "error_details": str(e),
                },
            )
```

## 重试策略

### 基本重试

```python
import asyncio

class RetryHandler:
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_multiplier: float = 2.0,
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier

    async def retry_with_backoff(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """带退避的重试"""
        last_exception = None
        delay = self.base_delay

        for attempt in range(self.max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                # 最后一次尝试失败
                if attempt == self.max_attempts - 1:
                    break

                # 等待后重试
                print(f"Attempt {attempt + 1} failed, retrying in {delay}s...")
                await asyncio.sleep(delay)

                # 增加延迟（指数退避）
                delay = min(delay * self.backoff_multiplier, self.max_delay)

        # 所有尝试都失败
        raise last_exception
```

### 可重试错误判断

```python
class RetryableErrorChecker:
    # 可重试的错误类型
    RETRYABLE_ERRORS = {
        ErrorType.AGENT_TIMEOUT,
        ErrorType.LLM_API_ERROR,
        ErrorType.LLM_RATE_LIMITED,
        ErrorType.NETWORK_ERROR,
        ErrorType.DATABASE_ERROR,
    }

    @classmethod
    def is_retryable(cls, result: AgentResult) -> bool:
        """判断结果是否可重试"""
        if result.success:
            return False

        error_type = result.metadata.get("error_type")

        return error_type in cls.RETRYABLE_ERRORS

    @classmethod
    def should_retry(cls, exception: Exception) -> bool:
        """判断异常是否可重试"""
        # 网络错误可重试
        if isinstance(exception, (TimeoutError, ConnectionError)):
            return True

        # API 错误可重试
        if "rate limit" in str(exception).lower():
            return True

        return False
```

### 重试中间件

```python
class RetryMiddleware(BaseMiddleware):
    def __init__(
        self,
        name: str,
        max_attempts: int = 3,
        retry_checker: RetryableErrorChecker = None,
    ):
        super().__init__(name)
        self.max_attempts = max_attempts
        self.retry_checker = retry_checker or RetryableErrorChecker()

    async def process(self, context: AgentContext) -> MiddlewareResult:
        """带重试的执行"""
        last_result = None

        for attempt in range(self.max_attempts):
            # 执行
            result = await self.call_next(context)

            # 成功或不可重试，直接返回
            if result.success or not self.retry_checker.is_retryable(result):
                return result

            last_result = result

            # 等待后重试
            delay = (attempt + 1) * 1.0  # 线性增长
            await asyncio.sleep(delay)

        return last_result
```

## 熔断器模式

```python
from enum import Enum
from datetime import datetime, timedelta

class CircuitState(Enum):
    CLOSED = "closed"       # 正常运行
    OPEN = "open"           # 熔断打开（阻止请求）
    HALF_OPEN = "half_open" # 半开（尝试恢复）

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
    ):
        """
        熔断器

        Args:
            failure_threshold: 失败阈值
            timeout: 熔断超时时间（秒）
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.opened_at = None

    async def call(self, func: Callable, *args, **kwargs):
        """通过熔断器调用函数"""

        # 检查熔断状态
        if self.state == CircuitState.OPEN:
            # 检查是否可以尝试恢复
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            # 执行函数
            result = await func(*args, **kwargs)

            # 成功，重置失败计数
            if self.state == CircuitState.HALF_OPEN:
                self._reset()

            return result

        except Exception as e:
            # 记录失败
            self._record_failure()

            # 达到阈值，打开熔断
            if self.failure_count >= self.failure_threshold:
                self._open()

            raise e

    def _record_failure(self):
        """记录失败"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

    def _open(self):
        """打开熔断"""
        self.state = CircuitState.OPEN
        self.opened_at = datetime.now()

    def _reset(self):
        """重置熔断"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.opened_at = None

    def _should_attempt_reset(self) -> bool:
        """是否应该尝试重置"""
        if self.opened_at is None:
            return False

        elapsed = (datetime.now() - self.opened_at).total_seconds()

        return elapsed >= self.timeout
```

## 错误恢复

### 优雅降级

```python
class GracefulDegradationMiddleware(BaseMiddleware):
    def __init__(self, name: str, fallback_response: str):
        super().__init__(name)
        self.fallback_response = fallback_response

    async def process(self, context: AgentContext) -> MiddlewareResult:
        """优雅降级"""
        try:
            result = await self.call_next(context)

            # 如果失败，返回降级响应
            if not result.success:
                return MiddlewareResult(
                    success=True,  # 返回成功但使用降级响应
                    agent_result=AgentResult(
                        success=True,
                        output=self.fallback_response,
                        metadata={"degraded": True},
                    ),
                )

            return result

        except Exception as e:
            # 任何异常都返回降级响应
            return MiddlewareResult(
                success=True,
                agent_result=AgentResult(
                    success=True,
                    output=self.fallback_response,
                    metadata={
                        "degraded": True,
                        "original_error": str(e),
                    },
                ),
            )
```

### 数据恢复

```python
class DataRecoveryHandler:
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager

    async def recover_from_checkpoint(
        self,
        session_id: str,
    ) -> Optional[Dict]:
        """从检查点恢复"""
        # 获取最新检查点
        checkpoint = await self.session_manager.get_latest_checkpoint(
            session_id
        )

        if checkpoint:
            print(f"Recovered from checkpoint: {checkpoint['checkpoint_id']}")
            return checkpoint["data"]

        return None

    async def save_recovery_point(
        self,
        session_id: str,
        data: Dict,
    ):
        """保存恢复点"""
        await self.session_manager.save_checkpoint(
            session_id,
            {
                "recovery_data": data,
                "timestamp": datetime.now().isoformat(),
            },
        )
```

## 错误监控

### 错误追踪

```python
class ErrorTracker:
    def __init__(self):
        self.errors = []
        self.error_counts = defaultdict(int)

    async def track_error(
        self,
        error: Exception,
        context: AgentContext = None,
    ):
        """追踪错误"""
        error_info = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": {
                "agent_id": context.agent_id if context else None,
                "user_id": context.user_id if context else None,
                "session_id": context.session_id if context else None,
            },
        }

        self.errors.append(error_info)
        self.error_counts[type(error).__name__] += 1

        # 严重错误立即告警
        if self._is_critical(error):
            await self._send_alert(error_info)

    def _is_critical(self, error: Exception) -> bool:
        """判断是否是严重错误"""
        critical_errors = [
            DatabaseError,
            SystemError,
            MemoryError,
        ]

        return any(isinstance(error, t) for t in critical_errors)

    async def _send_alert(self, error_info: dict):
        """发送告警"""
        # 发送到告警系统
        logger.critical(f"Critical error: {error_info}")
```

### 错误报告

```python
class ErrorReporter:
    def generate_error_report(
        self,
        errors: List[Dict],
    ) -> str:
        """生成错误报告"""
        report = {
            "total_errors": len(errors),
            "error_types": self._count_error_types(errors),
            "recent_errors": errors[-10:],  # 最近 10 个
            "critical_errors": [
                e for e in errors
                if self._is_critical_error(e)
            ],
        }

        return json.dumps(report, indent=2)

    def _count_error_types(self, errors: List[Dict]) -> Dict[str, int]:
        """统计错误类型"""
        counts = defaultdict(int)

        for error in errors:
            error_type = error.get("error_type", "unknown")
            counts[error_type] += 1

        return dict(counts)
```

## 最佳实践

### 1. 提供有用的错误消息

```python
# ✅ 好：具体的错误消息
return AgentResult(
    success=False,
    error="Input exceeds maximum length of 10000 characters (got 15000)",
    metadata={
        "max_length": 10000,
        "actual_length": 15000,
    },
)

# ❌ 不好：模糊的错误消息
return AgentResult(
    success=False,
    error="Invalid input",
)
```

### 2. 包含错误上下文

```python
# ✅ 好：包含上下文
return AgentResult(
    success=False,
    error="Failed to execute agent",
    metadata={
        "agent_id": context.agent_id,
        "user_id": context.user_id,
        "attempt": attempt,
        "total_attempts": max_attempts,
    },
)
```

### 3. 记录完整的错误堆栈

```python
import logging
import traceback

logger = logging.getLogger(__name__)

try:
    result = await executor.execute(context)
except Exception as e:
    # 记录完整堆栈
    logger.error(
        f"Execution failed for agent {context.agent_id}",
        exc_info=True,
        extra={
            "user_id": context.user_id,
            "stack_trace": traceback.format_exc(),
        },
    )
```

### 4. 区分用户错误和系统错误

```python
def is_user_error(error_type: str) -> bool:
    """判断是否是用户错误"""
    user_errors = {
        ErrorType.VALIDATION_ERROR,
        ErrorType.INVALID_INPUT,
        ErrorType.AUTHORIZATION_FAILED,
    }

    return error_type in user_errors

# 根据错误类型返回不同的消息
if is_user_error(result.metadata["error_type"]):
    # 用户错误：友好的提示
    message = "Please check your input and try again."
else:
    # 系统错误：通用消息
    message = "An error occurred. Please try again later."
```

## 相关文档

- [中间件开发](middleware.md) - 中间件错误处理
- [测试策略](testing.md) - 错误测试
- [性能优化](performance.md) - 错误处理性能
