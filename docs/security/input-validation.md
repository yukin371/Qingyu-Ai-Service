# 输入验证

本文档详细介绍如何验证和清洗用户输入，防止常见的 Web 攻击。

## 为什么需要输入验证

输入验证是第一道防线，防止：

- **SQL 注入** - 操纵数据库查询
- **XSS 攻击** - 注入恶意脚本
- **命令注入** - 执行系统命令
- **路径遍历** - 访问未授权文件
- **LDAP 注入** - 操纵 LDAP 查询

## 验证层次

```
┌─────────────────────────────────────────────────┐
│                   用户输入                       │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│              第1层: 类型验证                     │
│  - 检查数据类型                                  │
│  - 验证基本格式                                  │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│              第2层: 长度验证                     │
│  - 最小长度                                      │
│  - 最大长度                                      │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│              第3层: 格式验证                     │
│  - 正则表达式匹配                                │
│  - 模式验证                                      │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│              第4层: 内容验证                     │
│  - 危险模式检测                                  │
│  - 注入攻击防护                                  │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│              第5层: 业务验证                     │
│  - 业务规则检查                                  │
│  - 权限验证                                      │
└─────────────────────────────────────────────────┘
```

## 基本验证

### 1. 类型验证

```python
from typing import Any, Type, TypeVar, get_origin, get_args

T = TypeVar('T')

class TypeValidator:
    def validate(self, value: Any, expected_type: Type[T]) -> tuple[bool, str]:
        """
        验证值类型
        返回: (is_valid, error_message)
        """
        if value is None:
            return True, ""  # None 值通常允许

        # 处理 Optional 类型
        origin = get_origin(expected_type)
        if origin is Union:
            # 尝试每个类型
            for arg_type in get_args(expected_type):
                is_valid, _ = self.validate(value, arg_type)
                if is_valid:
                    return True, ""
            return False, f"Value must be one of {get_args(expected_type)}"

        # 处理 List 类型
        if origin is list:
            if not isinstance(value, list):
                return False, f"Expected list, got {type(value).__name__}"
            # 验证元素类型
            if get_args(expected_type):
                element_type = get_args(expected_type)[0]
                for i, item in enumerate(value):
                    is_valid, error = self.validate(item, element_type)
                    if not is_valid:
                        return False, f"List element {i}: {error}"
            return True, ""

        # 处理 Dict 类型
        if origin is dict:
            if not isinstance(value, dict):
                return False, f"Expected dict, got {type(value).__name__}"
            return True, ""

        # 基本类型
        if not isinstance(value, expected_type):
            return False, f"Expected {expected_type.__name__}, got {type(value).__name__}"

        return True, ""
```

### 2. 长度验证

```python
class LengthValidator:
    def __init__(
        self,
        min_length: int = 0,
        max_length: int = 10000,
    ):
        self.min_length = min_length
        self.max_length = max_length

    def validate(self, value: str) -> tuple[bool, str]:
        """
        验证字符串长度
        返回: (is_valid, error_message)
        """
        if not isinstance(value, str):
            return False, f"Expected string, got {type(value).__name__}"

        length = len(value)

        if length < self.min_length:
            return False, f"Length {length} is less than minimum {self.min_length}"

        if length > self.max_length:
            return False, f"Length {length} exceeds maximum {self.max_length}"

        return True, ""
```

### 3. 格式验证

```python
import re
from typing import Pattern

class FormatValidator:
    # 常用格式模式
    PATTERNS = {
        "email": re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        ),
        "phone": re.compile(
            r'^\+?[\d\s\-()]+$'
        ),
        "url": re.compile(
            r'^https?://[^\s/$.?#].[^\s]*$'
        ),
        "uuid": re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        ),
        "ipv4": re.compile(
            r'^(\d{1,3}\.){3}\d{1,3}$'
        ),
        "username": re.compile(
            r'^[a-zA-Z0-9_]{3,20}$'
        ),
    }

    def validate(self, value: str, format_type: str) -> tuple[bool, str]:
        """
        验证格式
        返回: (is_valid, error_message)
        """
        if format_type not in self.PATTERNS:
            return False, f"Unknown format type: {format_type}"

        pattern = self.PATTERNS[format_type]

        if not pattern.match(value):
            return False, f"Value does not match {format_type} format"

        return True, ""

    def validate_regex(self, value: str, pattern: Pattern) -> tuple[bool, str]:
        """使用自定义正则表达式验证"""
        if not pattern.match(value):
            return False, f"Value does not match required pattern"

        return True, ""
```

## 注入防护

### 1. SQL 注入防护

```python
class SQLInjectionGuard:
    # SQL 注入模式
    SQL_INJECTION_PATTERNS = [
        r"'.*'",  # 引号注入
        r'".*"',  # 双引号注入
        r"1=1",
        r"1\s*=\s*1",
        r"OR\s+1\s*=\s*1",
        r"AND\s+1\s*=\s*1",
        r"UNION\s+SELECT",
        r"DROP\s+TABLE",
        r"DELETE\s+FROM",
        r"INSERT\s+INTO",
        r"UPDATE\s+\w+\s+SET",
        r";--",  # 注释
        r"#",
        r"--",
        r"/\*.*\*/",  # 多行注释
    ]

    def detect_sql_injection(self, text: str) -> tuple[bool, list[str]]:
        """
        检测 SQL 注入
        返回: (has_injection, matched_patterns)
        """
        matched = []

        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                matched.append(pattern)

        return len(matched) > 0, matched

    def sanitize_for_sql(self, text: str) -> str:
        """清洗用于 SQL 的文本"""
        # 转义特殊字符
        escape_map = {
            "'": "''",
            "\\": "\\",
            "\0": "\\0",
            "\n": "\\n",
            "\r": "\\r",
            '"': '\\"',
            "\x1a": "\\Z",
        }

        for char, escaped in escape_map.items():
            text = text.replace(char, escaped)

        return text
```

### 2. XSS 防护

```python
import html

class XSSGuard:
    # XSS 模式
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",  # 事件处理器
        r"<iframe",
        r"<embed",
        r"<object",
        r"<link",
        r"<meta",
        r"<style",
        r"<img[^>]+src[^>]*script:",
    ]

    def detect_xss(self, text: str) -> tuple[bool, list[str]]:
        """
        检测 XSS 攻击
        返回: (has_xss, matched_patterns)
        """
        matched = []

        for pattern in self.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                matched.append(pattern)

        return len(matched) > 0, matched

    def escape_html(self, text: str) -> str:
        """HTML 转义"""
        return html.escape(text)

    def sanitize_html(self, text: str, allowed_tags: list = None) -> str:
        """清洗 HTML，只保留允许的标签"""
        if allowed_tags is None:
            allowed_tags = ["p", "br", "strong", "em", "u"]

        # 移除不允许的标签
        text = re.sub(
            r'<(?!\/?(' + '|'.join(allowed_tags) + r')\b)[^>]+>',
            '',
            text,
            flags=re.IGNORECASE
        )

        return text
```

### 3. 命令注入防护

```python
class CommandInjectionGuard:
    # 命令注入模式
    COMMAND_INJECTION_PATTERNS = [
        r'&&',  # 命令连接
        r'\|\|',  # 或
        r';',   # 命令分隔
        r'\$',  # 变量替换
        r'\(.*\)',  # 子 shell
        r'`.*`',  # 反引号执行
        r'\|',  # 管道
        r'>',   # 输出重定向
        r'<',   # 输入重定向
        r'rm\s+-rf',
        r'chmod',
        r'chown',
        r'/etc/',
        r'/bin/',
        r'/usr/bin/',
    ]

    def detect_command_injection(self, text: str) -> tuple[bool, list[str]]:
        """
        检测命令注入
        返回: (has_injection, matched_patterns)
        """
        matched = []

        for pattern in self.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, text):
                matched.append(pattern)

        return len(matched) > 0, matched

    def sanitize_for_command(self, text: str) -> str:
        """清洗用于命令行的文本"""
        # 移除或转义特殊字符
        dangerous_chars = ['&', '|', ';', '$', '(', ')', '<', '>', '`']

        for char in dangerous_chars:
            text = text.replace(char, f'\\{char}')

        return text
```

### 4. 路径遍历防护

```python
class PathTraversalGuard:
    # 路径遍历模式
    PATH_TRAVERSAL_PATTERNS = [
        r'\.\./',  # 父目录
        r'\.\.\\',  # Windows 父目录
        r'%2e%2e',  # URL 编码的 ..
        r'%252e',  # 双重编码
        r'\.\.%2f',
        r'\.\.%5c',
        r'/etc/passwd',
        r'c:\\windows',
    ]

    def detect_path_traversal(self, path: str) -> tuple[bool, list[str]]:
        """
        检测路径遍历
        返回: (has_traversal, matched_patterns)
        """
        matched = []

        for pattern in self.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, path, re.IGNORECASE):
                matched.append(pattern)

        return len(matched) > 0, matched

    def validate_path(self, path: str, allowed_dir: str) -> tuple[bool, str]:
        """
        验证路径在允许的目录内
        返回: (is_safe, safe_path)
        """
        import os

        # 规范化路径
        normalized = os.path.normpath(path)

        # 解析绝对路径
        absolute = os.path.abspath(os.path.join(allowed_dir, normalized))

        # 检查是否在允许的目录内
        if not absolute.startswith(os.path.abspath(allowed_dir)):
            return False, "Path traversal detected"

        return True, absolute
```

## 综合验证器

### 输入验证器

```python
from typing import Optional, List, Dict

class InputValidator:
    def __init__(self):
        self.type_validator = TypeValidator()
        self.length_validator = LengthValidator()
        self.format_validator = FormatValidator()
        self.sql_guard = SQLInjectionGuard()
        self.xss_guard = XSSGuard()
        self.command_guard = CommandInjectionGuard()
        self.path_guard = PathTraversalGuard()

    def validate(
        self,
        value: Any,
        validation_rules: Dict,
    ) -> tuple[bool, List[str]]:
        """
        综合验证
        返回: (is_valid, errors)
        """
        errors = []

        # 类型验证
        if "type" in validation_rules:
            is_valid, error = self.type_validator.validate(
                value,
                validation_rules["type"],
            )
            if not is_valid:
                errors.append(error)
                return False, errors

        # 只对字符串进行后续验证
        if not isinstance(value, str):
            return True, errors

        # 长度验证
        if "min_length" in validation_rules or "max_length" in validation_rules:
            min_len = validation_rules.get("min_length", 0)
            max_len = validation_rules.get("max_length", 10000)

            validator = LengthValidator(min_len, max_len)
            is_valid, error = validator.validate(value)
            if not is_valid:
                errors.append(error)

        # 格式验证
        if "format" in validation_rules:
            is_valid, error = self.format_validator.validate(
                value,
                validation_rules["format"],
            )
            if not is_valid:
                errors.append(error)

        # SQL 注入检测
        if "check_sql_injection" in validation_rules:
            has_injection, patterns = self.sql_guard.detect_sql_injection(value)
            if has_injection:
                errors.append(f"SQL injection detected: {patterns}")

        # XSS 检测
        if "check_xss" in validation_rules:
            has_xss, patterns = self.xss_guard.detect_xss(value)
            if has_xss:
                errors.append(f"XSS detected: {patterns}")

        # 命令注入检测
        if "check_command_injection" in validation_rules:
            has_injection, patterns = self.command_guard.detect_command_injection(value)
            if has_injection:
                errors.append(f"Command injection detected: {patterns}")

        # 路径遍历检测
        if "check_path_traversal" in validation_rules:
            has_traversal, patterns = self.path_guard.detect_path_traversal(value)
            if has_traversal:
                errors.append(f"Path traversal detected: {patterns}")

        return len(errors) == 0, errors
```

## 中间件实现

### 验证中间件

```python
from src.middleware.base import BaseMiddleware
from src.common.types.agent_types import AgentContext, MiddlewareResult, AgentResult

class ValidationMiddleware(BaseMiddleware):
    def __init__(
        self,
        name: str,
        validator: InputValidator,
        field_rules: Dict[str, Dict],
    ):
        super().__init__(name)
        self.validator = validator
        self.field_rules = field_rules

    async def process(self, context: AgentContext) -> MiddlewareResult:
        """验证输入"""

        # 验证 current_task
        if "current_task" in self.field_rules:
            is_valid, errors = self.validator.validate(
                context.current_task,
                self.field_rules["current_task"],
            )

            if not is_valid:
                await self._log_validation_failure(context, errors)

                return MiddlewareResult(
                    success=False,
                    agent_result=AgentResult(
                        success=False,
                        output="",
                        error=f"Validation failed: {', '.join(errors)}",
                        metadata={"validation_errors": errors},
                    ),
                    skip_rest=True,
                )

        # 验证 metadata 中的字段
        if context.metadata:
            for field, rules in self.field_rules.items():
                if field in context.metadata:
                    is_valid, errors = self.validator.validate(
                        context.metadata[field],
                        rules,
                    )

                    if not is_valid:
                        await self._log_validation_failure(context, errors)

                        return MiddlewareResult(
                            success=False,
                            agent_result=AgentResult(
                                success=False,
                                output="",
                                error=f"Validation failed for {field}: {', '.join(errors)}",
                                metadata={"validation_errors": errors},
                            ),
                            skip_rest=True,
                        )

        return await self.call_next(context)

    async def _log_validation_failure(
        self,
        context: AgentContext,
        errors: List[str],
    ):
        """记录验证失败"""
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(
            f"Input validation failed for agent {context.agent_id}",
            extra={
                "user_id": context.user_id,
                "agent_id": context.agent_id,
                "errors": errors,
            },
        )
```

## 使用示例

### 基本使用

```python
from src.middleware.pipeline import MiddlewarePipeline

# 定义验证规则
validation_rules = {
    "current_task": {
        "type": str,
        "min_length": 1,
        "max_length": 10000,
        "check_sql_injection": True,
        "check_xss": True,
        "check_command_injection": True,
    },
    "user_input": {
        "type": str,
        "max_length": 5000,
        "check_xss": True,
    },
    "email": {
        "type": str,
        "format": "email",
    },
}

# 创建验证器
validator = InputValidator()

# 创建中间件
validation_middleware = ValidationMiddleware(
    name="validation",
    validator=validator,
    field_rules=validation_rules,
)

# 添加到管道
pipeline = MiddlewarePipeline()
pipeline.add(validation_middleware)
```

### 自定义验证规则

```python
class CustomValidator(InputValidator):
    def validate_custom_business_rules(
        self,
        context: AgentContext,
    ) -> tuple[bool, str]:
        """自定义业务规则验证"""

        # 示例: 检查特定 Agent 不允许某些输入
        if context.agent_id == "financial_advisor":
            # 检查是否包含股票代码
            if re.search(r'\$[A-Z]{2,5}', context.current_task):
                return False, "Stock queries not allowed in this context"

        return True, ""

# 在中间件中使用
class CustomValidationMiddleware(ValidationMiddleware):
    def __init__(self, name: str, custom_validator: CustomValidator, **kwargs):
        super().__init__(name, **kwargs)
        self.custom_validator = custom_validator

    async def process(self, context: AgentContext) -> MiddlewareResult:
        # 先进行基本验证
        result = await super().process(context)

        if not result.success:
            return result

        # 自定义验证
        is_valid, error = self.custom_validator.validate_custom_business_rules(
            context,
        )

        if not is_valid:
            return MiddlewareResult(
                success=False,
                agent_result=AgentResult(
                    success=False,
                    output="",
                    error=error,
                ),
                skip_rest=True,
            )

        return await self.call_next(context)
```

## 测试

### 单元测试

```python
import pytest
from src.security.input_validator import InputValidator

def test_sql_injection_detection():
    """测试 SQL 注入检测"""
    validator = InputValidator()

    malicious = "1' OR '1'='1"
    has_injection, patterns = validator.sql_guard.detect_sql_injection(malicious)

    assert has_injection is True
    assert len(patterns) > 0

def test_xss_detection():
    """测试 XSS 检测"""
    validator = InputValidator()

    malicious = "<script>alert('XSS')</script>"
    has_xss, patterns = validator.xss_guard.detect_xss(malicious)

    assert has_xss is True
    assert len(patterns) > 0

def test_command_injection_detection():
    """测试命令注入检测"""
    validator = InputValidator()

    malicious = "file.txt; rm -rf /"
    has_injection, patterns = validator.command_guard.detect_command_injection(malicious)

    assert has_injection is True
    assert len(patterns) > 0

def test_safe_input_passes():
    """测试安全输入通过"""
    validator = InputValidator()

    safe_input = "What is the capital of France?"

    rules = {
        "type": str,
        "min_length": 1,
        "max_length": 100,
        "check_sql_injection": True,
        "check_xss": True,
    }

    is_valid, errors = validator.validate(safe_input, rules)

    assert is_valid is True
    assert len(errors) == 0
```

## 最佳实践

### 1. 白名单优先

```python
# ✅ 好: 使用白名单
ALLOWED_TAGS = ["p", "br", "strong", "em"]

# ❌ 不好: 使用黑名单
BLOCKED_TAGS = ["script", "iframe", "object"]  # 可能遗漏
```

### 2. 验证时机

```python
# 在多个层次验证
class MultiLayerValidation:
    async def validate(self, data):
        # 第1层: 客户端验证（已在浏览器完成）
        # 第2层: API 入口验证
        is_valid = await self.api_gateway_validate(data)
        if not is_valid:
            return False

        # 第3层: 业务逻辑验证
        is_valid = await self.business_validate(data)
        if not is_valid:
            return False

        # 第4层: 数据库层验证
        is_valid = await self.database_validate(data)
        return is_valid
```

### 3. 错误处理

```python
def safe_validation_error(error: Exception) -> str:
    """返回安全的错误消息（不泄露内部信息）"""
    # 开发环境: 返回详细错误
    if os.getenv("ENV") == "development":
        return str(error)

    # 生产环境: 返回通用消息
    return "Input validation failed"
```

## 相关文档

- [安全概述](overview.md) - 整体安全架构
- [提示词注入防护](prompt-injection.md) - AI 特定输入验证
- [认证授权](auth.md) - 访问控制
- [输出清洗](output-sanitization.md) - 输出安全
