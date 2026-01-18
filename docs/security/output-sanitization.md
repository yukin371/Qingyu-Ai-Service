# 输出清洗

本文档介绍如何清洗 Agent 的输出，防止恶意内容泄露和 XSS 攻击。

## 为什么需要输出清洗

AI Agent 的输出可能包含：

1. **恶意脚本** - LLM 被诱导生成 JavaScript/HTML
2. **敏感信息** - API 密钥、密码、PII 数据
3. **危险内容** - SQL 注入、命令注入
4. **超长输出** - 导致资源耗尽

## 清洗策略

### 1. HTML 转义

防止 XSS 攻击：

```python
import html
import re

class OutputSanitizer:
    def __init__(self):
        self.escape_html = True
        self.remove_scripts = True
        self.max_length = 50000

    def sanitize(self, text: str) -> str:
        """清洗输出文本"""
        if not text:
            return text

        # 1. 截断超长输出
        if len(text) > self.max_length:
            text = text[:self.max_length] + "... [truncated]"

        # 2. HTML 转义
        if self.escape_html:
            text = html.escape(text)

        # 3. 移除脚本标签
        if self.remove_scripts:
            text = self._remove_scripts(text)

        # 4. 移除事件处理器
        text = self._remove_event_handlers(text)

        # 5. 移除危险协议
        text = self._remove_dangerous_protocols(text)

        return text

    def _remove_scripts(self, text: str) -> str:
        """移除脚本标签"""
        # 移除 <script> 标签
        text = re.sub(
            r'<script[^>]*>.*?</script>',
            '',
            text,
            flags=re.IGNORECASE | re.DOTALL
        )

        # 移除 JavaScript 实体
        text = re.sub(
            r'&#[0-9]+;',
            '',
            text
        )

        return text

    def _remove_event_handlers(self, text: str) -> str:
        """移除事件处理器"""
        event_handlers = [
            r'on\w+\s*=',
            r'onload\s*=',
            r'onerror\s*=',
            r'onclick\s*=',
            r'onmouseover\s*=',
        ]

        for pattern in event_handlers:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        return text

    def _remove_dangerous_protocols(self, text: str) -> str:
        """移除危险协议"""
        dangerous_protocols = [
            r'javascript:',
            r'data:',
            r'vbscript:',
        ]

        for protocol in dangerous_protocols:
            text = re.sub(
                protocol,
                '',
                text,
                flags=re.IGNORECASE
            )

        return text
```

### 2. 敏感信息检测

检测和移除敏感信息：

```python
import re
from typing import List, Tuple

class SensitiveDataDetector:
    def __init__(self):
        # PII 模式
        self.pii_patterns = {
            'ssn': r'\d{3}-\d{2}-\d{4}',
            'credit_card': r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}',
            'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            'phone': r'\+?[\d\s\-()]{10,}',
            'ip_address': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
        }

        # 密钥模式
        self.key_patterns = {
            'api_key': r'(api[_-]?key|apikey)\s*[:=]\s*[\'"]?([a-zA-Z0-9_\-]{20,})',
            'secret': r'(secret|password|passwd)\s*[:=]\s*[\'"]?(\S{8,})',
            'token': r'(token|access_token)\s*[:=]\s*[\'"]?([a-zA-Z0-9_\-\.]{20,})',
            'aws_key': r'AKIA[0-9A-Z]{16}',
            'sk_key': r'sk-[a-zA-Z0-9]{20,}',
        }

    def detect_and_redact(self, text: str) -> Tuple[str, List[dict]]:
        """
        检测并编辑敏感信息
        返回: (清洗后的文本, 检测到的敏感信息列表)
        """
        detections = []
        redacted_text = text

        # 检测 PII
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                detections.append({
                    'type': 'pii',
                    'pii_type': pii_type,
                    'value': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                })

                # 编辑
                redacted_text = (
                    redacted_text[:match.start()] +
                    f'[REDACTED {pii_type.upper()}]' +
                    redacted_text[match.end():]
                )

        # 检测密钥
        for key_type, pattern in self.key_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # 获取实际的密钥值（第二个捕获组）
                key_value = match.group(2) if match.lastindex >= 2 else match.group(1)

                detections.append({
                    'type': 'credential',
                    'key_type': key_type,
                    'value': key_value[:10] + '...',  # 只记录前几个字符
                    'start': match.start(),
                    'end': match.end(),
                })

                # 编辑
                redacted_text = (
                    redacted_text[:match.start()] +
                    '[REDACTED CREDENTIAL]' +
                    redacted_text[match.end():]
                )

        return redacted_text, detections
```

### 3. 输出验证

验证输出不包含恶意内容：

```python
class OutputValidator:
    def __init__(self):
        # 危险模式
        self.dangerous_patterns = {
            'sql_injection': [
                r"'.*'",  # 引号注入
                r'1=1',
                r'UNION\s+SELECT',
                r'DROP\s+TABLE',
                r';--',
            ],
            'command_injection': [
                r'&&',
                r'\|\|',
                r';',
                r'\$\(.*\)',
                r'`.*`',
                r'rm\s+-rf',
            ],
            'path_traversal': [
                r'\.\./',
                r'\.\.\\',
                r'/etc/passwd',
            ],
        }

    def validate(self, text: str) -> Tuple[bool, List[str]]:
        """
        验证输出是否安全
        返回: (is_safe, 检测到的威胁列表)
        """
        threats = []

        for threat_type, patterns in self.dangerous_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    threats.append(f"{threat_type}: {pattern}")

        return len(threats) == 0, threats

    def sanitize_threats(self, text: str) -> str:
        """移除检测到的威胁"""
        safe_text = text

        for patterns in self.dangerous_patterns.values():
            for pattern in patterns:
                safe_text = re.sub(
                    pattern,
                    '[REMOVED]',
                    safe_text,
                    flags=re.IGNORECASE
                )

        return safe_text
```

## 中间件实现

### 输出清洗中间件

```python
from src.middleware.base import BaseMiddleware
from src.common.types.agent_types import AgentContext, MiddlewareResult, AgentResult

class OutputSanitizationMiddleware(BaseMiddleware):
    def __init__(
        self,
        name: str,
        sanitize_html: bool = True,
        remove_pii: bool = True,
        remove_credentials: bool = True,
        max_length: int = 50000,
    ):
        super().__init__(name)
        self.sanitize_html = sanitize_html
        self.remove_pii = remove_pii
        self.remove_credentials = remove_credentials
        self.max_length = max_length

        # 初始化清洗器
        self.output_sanitizer = OutputSanitizer()
        self.pii_detector = SensitiveDataDetector()
        self.output_validator = OutputValidator()

    async def process(self, context: AgentContext) -> MiddlewareResult:
        """处理并清洗输出"""

        # 执行 Agent
        result = await self.call_next(context)

        # 如果失败，直接返回
        if not result.success:
            return result

        # 获取输出
        output = result.agent_result.output

        if not output:
            return result

        # 1. HTML 清洗
        if self.sanitize_html:
            output = self.output_sanitizer.sanitize(output)

        # 2. 移除 PII
        if self.remove_pii:
            output, pii_detections = self.pii_detector.detect_and_redact(output)

            # 记录检测
            if pii_detections:
                await self._log_pii_detection(context, pii_detections)

        # 3. 移除凭据
        if self.remove_credentials:
            output, cred_detections = self.pii_detector.detect_and_redact(output)

            # 记录检测
            if cred_detections:
                await self._log_credential_detection(context, cred_detections)

        # 4. 验证输出
        is_safe, threats = self.output_validator.validate(output)

        if not is_safe:
            # 记录威胁
            await self._log_threat_detection(context, threats)

            # 移除威胁
            output = self.output_validator.sanitize_threats(output)

        # 5. 更新结果
        result.agent_result.output = output

        return result

    async def _log_pii_detection(
        self,
        context: AgentContext,
        detections: list
    ):
        """记录 PII 检测"""
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(
            f"PII detected in output for agent {context.agent_id}",
            extra={
                "user_id": context.user_id,
                "agent_id": context.agent_id,
                "detections": detections,
            },
        )

    async def _log_credential_detection(
        self,
        context: AgentContext,
        detections: list
    ):
        """记录凭据检测"""
        import logging

        logger = logging.getLogger(__name__)
        logger.critical(
            f"Credentials detected in output for agent {context.agent_id}",
            extra={
                "user_id": context.user_id,
                "agent_id": context.agent_id,
                "detections": detections,
            },
        )

    async def _log_threat_detection(
        self,
        context: AgentContext,
        threats: list
    ):
        """记录威胁检测"""
        import logging

        logger = logging.getLogger(__name__)
        logger.error(
            f"Security threats detected in output for agent {context.agent_id}",
            extra={
                "user_id": context.user_id,
                "agent_id": context.agent_id,
                "threats": threats,
            },
        )
```

## 使用示例

### 基本使用

```python
from src.middleware.pipeline import MiddlewarePipeline

# 创建清洗中间件
sanitizer = OutputSanitizationMiddleware(
    name="output_sanitizer",
    sanitize_html=True,
    remove_pii=True,
    remove_credentials=True,
    max_length=50000,
)

# 添加到管道
pipeline = MiddlewarePipeline()
pipeline.add(sanitizer)

# 应用到执行器
executor.set_middleware_pipeline(pipeline)
```

### 自定义清洗规则

```python
class CustomOutputSanitizer(OutputSanitizationMiddleware):
    def __init__(self, name: str, custom_patterns: dict):
        super().__init__(name)
        self.custom_patterns = custom_patterns

    async def process(self, context: AgentContext) -> MiddlewareResult:
        result = await self.call_next(context)

        if not result.success:
            return result

        output = result.agent_result.output

        # 应用自定义清洗
        for threat_type, patterns in self.custom_patterns.items():
            for pattern in patterns:
                if re.search(pattern, output, re.IGNORECASE):
                    # 记录并移除
                    await self._log_custom_detection(context, threat_type)
                    output = re.sub(
                        pattern,
                        '[REMOVED]',
                        output,
                        flags=re.IGNORECASE
                    )

        result.agent_result.output = output
        return result

    async def _log_custom_detection(
        self,
        context: AgentContext,
        threat_type: str
    ):
        """记录自定义威胁检测"""
        logging.warning(
            f"Custom threat '{threat_type}' detected in output",
            extra={"agent_id": context.agent_id}
        )
```

## 测试

### 单元测试

```python
import pytest
from src.security.output_sanitizer import OutputSanitizer, SensitiveDataDetector

def test_html_escaping():
    """测试 HTML 转义"""
    sanitizer = OutputSanitizer()

    input_text = '<script>alert("XSS")</script>Hello'
    output = sanitizer.sanitize(input_text)

    assert '<script>' not in output
    assert '&lt;script&gt;' in output

def test_pii_detection():
    """测试 PII 检测"""
    detector = SensitiveDataDetector()

    input_text = "User's SSN is 123-45-6789"
    output, detections = detector.detect_and_redact(input_text)

    assert '123-45-6789' not in output
    assert '[REDACTED SSN]' in output
    assert len(detections) == 1

def test_api_key_detection():
    """测试 API 密钥检测"""
    detector = SensitiveDataDetector()

    input_text = "API key: sk-1234567890abcdef1234567890abcdef"
    output, detections = detector.detect_and_redact(input_text)

    assert 'sk-1234567890abcdef' not in output
    assert '[REDACTED CREDENTIAL]' in output

def test_output_truncation():
    """测试输出截断"""
    sanitizer = OutputSanitizer()
    sanitizer.max_length = 100

    long_text = "A" * 1000
    output = sanitizer.sanitize(long_text)

    assert len(output) <= 120  # 100 + "... [truncated]"
```

### 集成测试

```python
@pytest.mark.asyncio
async def test_middleware_sanitizes_output():
    """测试中间件清洗输出"""
    middleware = OutputSanitizationMiddleware(
        name="test_sanitizer",
        remove_pii=True,
    )

    # Mock call_next 返回包含敏感信息的输出
    mock_result = MiddlewareResult(
        success=True,
        agent_result=AgentResult(
            success=True,
            output="User's email is user@example.com",
        ),
    )

    middleware.call_next = AsyncMock(return_value=mock_result)

    context = AgentContext(
        agent_id="test_agent",
        user_id="test_user",
        session_id="test_session",
        current_task="Test",
    )

    result = await middleware.process(context)

    assert result.success is True
    assert 'user@example.com' not in result.agent_result.output
    assert '[REDACTED]' in result.agent_result.output
```

## 性能考虑

### 缓存编译后的正则表达式

```python
import re
from functools import lru_cache

class CachedPatternMatcher:
    def __init__(self):
        self._pattern_cache = {}

    def compile_pattern(self, pattern: str) -> re.Pattern:
        """编译并缓存模式"""
        if pattern not in self._pattern_cache:
            self._pattern_cache[pattern] = re.compile(pattern, re.IGNORECASE)

        return self._pattern_cache[pattern]

    @lru_cache(maxsize=1000)
    def match(self, pattern: str, text: str) -> bool:
        """匹配模式（带缓存）"""
        compiled = self.compile_pattern(pattern)
        return bool(compiled.search(text))
```

### 并行处理

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class ParallelOutputSanitizer:
    def __init__(self, max_workers=4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def sanitize_multiple(self, texts: List[str]) -> List[str]:
        """并行清洗多个输出"""
        loop = asyncio.get_event_loop()

        tasks = [
            loop.run_in_executor(self.executor, self._sanitize, text)
            for text in texts
        ]

        return await asyncio.gather(*tasks)

    def _sanitize(self, text: str) -> str:
        """同步清洗"""
        # 清洗逻辑
        return text
```

## 最佳实践

### 1. 分层清洗

```python
# 不同层级的清洗
class LayeredOutputSanitizer:
    def __init__(self):
        # 第1层：基本 HTML 清洗
        self.basic_sanitizer = OutputSanitizer()

        # 第2层：PII 检测
        self.pii_detector = SensitiveDataDetector()

        # 第3层：深度验证
        self.deep_validator = OutputValidator()

    async def sanitize(self, text: str) -> str:
        """多层清洗"""
        # 基本清洗
        text = self.basic_sanitizer.sanitize(text)

        # PII 移除
        text, _ = self.pii_detector.detect_and_redact(text)

        # 深度验证
        is_safe, threats = self.deep_validator.validate(text)
        if not is_safe:
            text = self.deep_validator.sanitize_threats(text)

        return text
```

### 2. 可配置清洗

```python
class ConfigurableOutputSanitizer:
    def __init__(self, config: dict):
        self.config = config

    def should_sanitize(self, feature: str) -> bool:
        """检查是否应该清洗某个特性"""
        return self.config.get(f"sanitize_{feature}", True)

    async def process(self, context: AgentContext) -> MiddlewareResult:
        result = await self.call_next(context)

        if not result.success:
            return result

        output = result.agent_result.output

        # 根据配置清洗
        if self.should_sanitize("html"):
            output = self._sanitize_html(output)

        if self.should_sanitize("pii"):
            output = self._sanitize_pii(output)

        if self.should_sanitize("credentials"):
            output = self._sanitize_credentials(output)

        result.agent_result.output = output
        return result
```

### 3. 审计日志

```python
class AuditingOutputSanitizer(OutputSanitizationMiddleware):
    async def _log_sanitization(
        self,
        context: AgentContext,
        original: str,
        sanitized: str,
        changes: list
    ):
        """记录所有清洗操作"""
        audit_log = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": context.agent_id,
            "user_id": context.user_id,
            "original_length": len(original),
            "sanitized_length": len(sanitized),
            "changes": changes,
        }

        # 写入审计日志
        await self.audit_logger.log(audit_log)
```

## 相关文档

- [安全概述](overview.md) - 整体安全架构
- [提示词注入防护](prompt-injection.md) - 输入安全
- [认证授权](auth.md) - 访问控制
- [数据保护](data-protection.md) - 敏感数据保护
