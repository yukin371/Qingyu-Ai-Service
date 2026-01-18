# 数据保护

本文档介绍如何保护敏感数据，包括加密、访问控制和数据生命周期管理。

## 敏感数据类型

### PII (个人身份信息)

| 数据类型 | 示例 | 风险等级 |
|---------|------|---------|
| 姓名 | "John Doe" | 🟡 中 |
| 地址 | "123 Main St" | 🟡 中 |
| 电话 | "+1-555-1234" | 🟡 中 |
| 邮箱 | "user@example.com" | 🟡 中 |
| SSN | "123-45-6789" | 🔴 高 |
| 信用卡 | "4532-1234-5678-9010" | 🔴 高 |
| 护照号 | "A12345678" | 🔴 高 |

### 凭据

| 数据类型 | 示例 | 风险等级 |
|---------|------|---------|
| API 密钥 | "sk-1234567890abcdef" | 🔴 高 |
| 密码 | "P@ssw0rd!" | 🔴 高 |
| Token | "eyJhbGciOi..." | 🔴 高 |
| 访问密钥 | "AKIAIOSFODNN7EXAMPLE" | 🔴 高 |

## 数据分类

### 分类标准

```python
from enum import Enum

class DataClassification(Enum):
    PUBLIC = "public"         # 公开数据
    INTERNAL = "internal"     # 内部数据
    CONFIDENTIAL = "confidential"  # 机密数据
    RESTRICTED = "restricted"      # 限制数据

class DataClassifier:
    def classify_data(self, data: str, context: dict) -> DataClassification:
        """分类数据"""

        # 检查是否包含 PII
        if self._contains_pii(data):
            return DataClassification.CONFIDENTIAL

        # 检查是否包含凭据
        if self._contains_credentials(data):
            return DataClassification.RESTRICTED

        # 检查是否是内部信息
        if self._is_internal(data, context):
            return DataClassification.INTERNAL

        return DataClassification.PUBLIC

    def _contains_pii(self, data: str) -> bool:
        """检查是否包含 PII"""
        pii_patterns = [
            r'\d{3}-\d{2}-\d{4}',  # SSN
            r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}',  # 信用卡
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  # 邮箱
        ]

        for pattern in pii_patterns:
            if re.search(pattern, data):
                return True

        return False

    def _contains_credentials(self, data: str) -> bool:
        """检查是否包含凭据"""
        cred_patterns = [
            r'sk-[a-zA-Z0-9]{20,}',
            r'api[_-]?key[\'"]?\s*[:=]\s*[\'"]?[a-zA-Z0-9]{20,}',
            r'password[\'"]?\s*[:=]\s*[\'"]?\S{8,}',
        ]

        for pattern in cred_patterns:
            if re.search(pattern, data, re.IGNORECASE):
                return True

        return False

    def _is_internal(self, data: str, context: dict) -> bool:
        """检查是否是内部信息"""
        # 检查上下文
        if context.get("source") in ["internal_db", "internal_api"]:
            return True

        # 检查标记
        if data.startswith("[INTERNAL]"):
            return True

        return False
```

## 加密

### 对称加密

```python
from cryptography.fernet import Fernet
import base64
import os

class SymmetricEncryption:
    def __init__(self, key: bytes = None):
        """
        初始化加密器
        key: 32 字节的加密密钥
        """
        if key:
            if len(key) != 32:
                raise ValueError("Key must be 32 bytes")
            self.key = base64.urlsafe_b64encode(key)
        else:
            # 生成新密钥
            self.key = Fernet.generate_key()

        self.cipher = Fernet(self.key)

    def encrypt(self, data: str) -> bytes:
        """加密数据"""
        encrypted = self.cipher.encrypt(data.encode())
        return encrypted

    def decrypt(self, encrypted_data: bytes) -> str:
        """解密数据"""
        decrypted = self.cipher.decrypt(encrypted_data)
        return decrypted.decode()

    def encrypt_dict(self, data: dict, fields: list) -> dict:
        """加密字典中的特定字段"""
        encrypted = data.copy()

        for field in fields:
            if field in encrypted:
                value = encrypted[field]
                if isinstance(value, str):
                    encrypted[field] = self.encrypt(value).decode()

        return encrypted

    def decrypt_dict(self, data: dict, fields: list) -> dict:
        """解密字典中的特定字段"""
        decrypted = data.copy()

        for field in fields:
            if field in decrypted:
                value = decrypted[field]
                if isinstance(value, str):
                    decrypted[field] = self.decrypt(value.encode())

        return decrypted
```

### 哈希

```python
import hashlib
import hmac

class DataHashing:
    @staticmethod
    def hash_password(password: str, salt: str = None) -> tuple[str, str]:
        """
        哈希密码
        返回: (hashed_password, salt)
        """
        if salt is None:
            salt = os.urandom(32).hex()

        # 使用 PBKDF2
        hashed = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt.encode(),
            100000,  # 迭代次数
        )

        return hashed.hex(), salt

    @staticmethod
    def verify_password(password: str, hashed: str, salt: str) -> bool:
        """验证密码"""
        computed_hash, _ = DataHashing.hash_password(password, salt)
        return hmac.compare_digest(computed_hash, hashed)

    @staticmethod
    def hash_data(data: str) -> str:
        """哈希数据（SHA-256）"""
        return hashlib.sha256(data.encode()).hexdigest()

    @staticmethod
    def hash_file(file_path: str) -> str:
        """哈希文件"""
        sha256_hash = hashlib.sha256()

        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        return sha256_hash.hexdigest()
```

### 密钥管理

```python
from typing import Optional
import os

class KeyManager:
    def __init__(self):
        self.keys = {}
        self.key_store = os.getenv("KEY_STORE_PATH", "/secure/keys")

    def generate_key(self, key_id: str) -> bytes:
        """生成新密钥"""
        key = os.urandom(32)
        self.keys[key_id] = key

        # 持久化到安全存储
        self._store_key(key_id, key)

        return key

    def get_key(self, key_id: str) -> Optional[bytes]:
        """获取密钥"""
        # 先从内存获取
        if key_id in self.keys:
            return self.keys[key_id]

        # 从存储加载
        key = self._load_key(key_id)
        if key:
            self.keys[key_id] = key

        return key

    def rotate_key(self, key_id: str) -> bytes:
        """轮换密钥"""
        old_key = self.get_key(key_id)

        # 生成新密钥
        new_key = self.generate_key(key_id)

        # 重新加密使用旧密钥的数据
        self._reencrypt_data(key_id, old_key, new_key)

        return new_key

    def _store_key(self, key_id: str, key: bytes):
        """存储密钥到安全位置"""
        # 实际实现应该使用 HSM 或密钥管理服务
        key_path = os.path.join(self.key_store, f"{key_id}.key")

        with open(key_path, "wb") as f:
            f.write(key)

        # 设置严格权限
        os.chmod(key_path, 0o600)

    def _load_key(self, key_id: str) -> Optional[bytes]:
        """从安全位置加载密钥"""
        key_path = os.path.join(self.key_store, f"{key_id}.key")

        if not os.path.exists(key_path):
            return None

        with open(key_path, "rb") as f:
            return f.read()

    def _reencrypt_data(self, key_id: str, old_key: bytes, new_key: bytes):
        """使用新密钥重新加密数据"""
        # 实现数据重新加密
        pass
```

## 访问控制

### 基于属性的访问控制 (ABAC)

```python
from typing import Dict, List, Any

class ABACPolicy:
    def __init__(self):
        self.policies = []

    def add_policy(self, policy: Dict[str, Any]):
        """添加策略"""
        self.policies.append(policy)

    def evaluate(
        self,
        subject: Dict,  # 用户属性
        resource: Dict,  # 资源属性
        action: str,     # 操作
        environment: Dict,  # 环境属性
    ) -> bool:
        """评估访问请求"""

        for policy in self.policies:
            if self._matches_policy(subject, resource, action, environment, policy):
                return policy.get("effect", "deny") == "permit"

        return False  # 默认拒绝

    def _matches_policy(
        self,
        subject: Dict,
        resource: Dict,
        action: str,
        environment: Dict,
        policy: Dict,
    ) -> bool:
        """检查是否匹配策略"""

        # 检查主体匹配
        if "subject" in policy:
            if not self._match_attributes(subject, policy["subject"]):
                return False

        # 检查资源匹配
        if "resource" in policy:
            if not self._match_attributes(resource, policy["resource"]):
                return False

        # 检查操作匹配
        if "action" in policy:
            if action not in policy["action"]:
                return False

        # 检查环境匹配
        if "environment" in policy:
            if not self._match_attributes(environment, policy["environment"]):
                return False

        return True

    def _match_attributes(self, attributes: Dict, rules: Dict) -> bool:
        """匹配属性"""
        for key, value in rules.items():
            if key not in attributes:
                return False

            if isinstance(value, list):
                if attributes[key] not in value:
                    return False
            else:
                if attributes[key] != value:
                    return False

        return True

# 使用示例
policy_engine = ABACPolicy()

# 策略 1: 管理员可以访问所有资源
policy_engine.add_policy({
    "effect": "permit",
    "subject": {"role": "admin"},
    "action": ["read", "write", "delete"],
})

# 策略 2: 高级用户可以访问机密数据
policy_engine.add_policy({
    "effect": "permit",
    "subject": {"tier": "premium"},
    "resource": {"classification": "confidential"},
    "action": ["read"],
})

# 策略 3: 工作时间访问
policy_engine.add_policy({
    "effect": "permit",
    "subject": {"role": "user"},
    "resource": {"classification": "internal"},
    "action": ["read"],
    "environment": {"hour": range(9, 18)},  # 9AM - 6PM
})
```

### 数据脱敏

```python
import re
from typing import Any

class DataMasker:
    def mask_data(self, data: Any, rules: Dict) -> Any:
        """根据规则脱敏数据"""

        if isinstance(data, dict):
            return self._mask_dict(data, rules)

        elif isinstance(data, list):
            return [self.mask_data(item, rules) for item in data]

        elif isinstance(data, str):
            return self._mask_string(data, rules)

        return data

    def _mask_dict(self, data: Dict, rules: Dict) -> Dict:
        """脱敏字典"""
        masked = {}

        for key, value in data.items():
            if key in rules:
                # 应用脱敏规则
                mask_rule = rules[key]
                masked[key] = self._apply_mask(value, mask_rule)
            else:
                masked[key] = value

        return masked

    def _mask_string(self, data: str, rules: Dict) -> str:
        """脱敏字符串"""
        for pattern, mask_rule in rules.items():
            if re.search(pattern, data):
                return self._apply_mask(data, mask_rule)

        return data

    def _apply_mask(self, value: Any, mask_rule: str) -> Any:
        """应用脱敏规则"""

        if mask_rule == "email":
            return self._mask_email(value)

        elif mask_rule == "phone":
            return self._mask_phone(value)

        elif mask_rule == "credit_card":
            return self._mask_credit_card(value)

        elif mask_rule == "ssn":
            return self._mask_ssn(value)

        elif mask_rule == "partial":
            return self._mask_partial(value)

        elif mask_rule == "full":
            return "***"

        return value

    @staticmethod
    def _mask_email(email: str) -> str:
        """脱敏邮箱"""
        if "@" not in email:
            return email

        username, domain = email.split("@", 1)

        if len(username) <= 2:
            masked_username = "*" * len(username)
        else:
            masked_username = username[0] + "*" * (len(username) - 2) + username[-1]

        return f"{masked_username}@{domain}"

    @staticmethod
    def _mask_phone(phone: str) -> str:
        """脱敏电话"""
        # 移除非数字字符
        digits = re.sub(r'\D', '', phone)

        if len(digits) < 4:
            return "***"

        # 显示最后 4 位
        return "*" * (len(digits) - 4) + digits[-4:]

    @staticmethod
    def _mask_credit_card(card: str) -> str:
        """脱敏信用卡"""
        digits = re.sub(r'\D', '', card)

        if len(digits) < 4:
            return "***"

        # 显示最后 4 位
        return "*" * 12 + digits[-4:]

    @staticmethod
    def _mask_ssn(ssn: str) -> str:
        """脱敏 SSN"""
        return "***-**-****"

    @staticmethod
    def _mask_partial(value: str, visible_chars: int = 4) -> str:
        """部分脱敏"""
        if len(value) <= visible_chars:
            return "*" * len(value)

        return value[:visible_chars] + "*" * (len(value) - visible_chars)

# 使用示例
masker = DataMasker()

rules = {
    "email": "email",
    "phone": "phone",
    "ssn": "ssn",
    "credit_card": "credit_card",
    "password": "full",
}

user_data = {
    "name": "John Doe",
    "email": "john.doe@example.com",
    "phone": "+1-555-123-4567",
    "ssn": "123-45-6789",
    "password": "SecretPassword123",
}

masked_data = masker.mask_data(user_data, rules)
# {
#     "name": "John Doe",
#     "email": "j***@example.com",
#     "phone": "*******4567",
#     "ssn": "***-**-****",
#     "password": "***",
# }
```

## 数据生命周期

### 数据保留策略

```python
from datetime import datetime, timedelta
from typing import List

class DataRetentionPolicy:
    def __init__(self):
        self.policies = {}

    def add_policy(
        self,
        data_type: str,
        retention_period: timedelta,
        archive_after: timedelta = None,
    ):
        """添加保留策略"""
        self.policies[data_type] = {
            "retention_period": retention_period,
            "archive_after": archive_after,
        }

    def should_retain(self, data_type: str, created_at: datetime) -> bool:
        """检查数据是否应该保留"""
        if data_type not in self.policies:
            return True  # 默认保留

        policy = self.policies[data_type]
        expiry = created_at + policy["retention_period"]

        return datetime.now() < expiry

    def should_archive(self, data_type: str, created_at: datetime) -> bool:
        """检查数据是否应该归档"""
        if data_type not in self.policies:
            return False

        policy = self.policies[data_type]

        if policy["archive_after"] is None:
            return False

        archive_time = created_at + policy["archive_after"]

        return datetime.now() >= archive_time
```

### 数据清理

```python
class DataCleaner:
    def __init__(self, retention_policy: DataRetentionPolicy):
        self.policy = retention_policy

    async def clean_expired_data(self, data_store: List[Dict]):
        """清理过期数据"""
        kept = []
        archived = []
        deleted = []

        for item in data_store:
            data_type = item.get("type", "unknown")
            created_at = item.get("created_at", datetime.now())

            # 检查是否应该保留
            if not self.policy.should_retain(data_type, created_at):
                deleted.append(item)
                continue

            # 检查是否应该归档
            if self.policy.should_archive(data_type, created_at):
                archived.append(item)
            else:
                kept.append(item)

        return {
            "kept": kept,
            "archived": archived,
            "deleted": deleted,
        }

    async def delete_data(self, data: Dict):
        """安全删除数据"""
        # 1. 软删除（标记为已删除）
        data["deleted"] = True
        data["deleted_at"] = datetime.now()

        # 2. 如果是敏感数据，先擦除内容
        if self._is_sensitive(data):
            await self._wipe_sensitive_data(data)

        # 3. 从数据库删除
        await self._delete_from_database(data)

    async def _wipe_sensitive_data(self, data: Dict):
        """擦除敏感数据"""
        sensitive_fields = ["password", "ssn", "credit_card", "api_key"]

        for field in sensitive_fields:
            if field in data:
                # 覆盖多次
                for _ in range(3):
                    data[field] = os.urandom(len(str(data[field])))

                # 最终设置为空
                data[field] = None

    def _is_sensitive(self, data: Dict) -> bool:
        """检查是否是敏感数据"""
        classification = data.get("classification", "public")
        return classification in ["confidential", "restricted"]
```

## 审计日志

```python
import logging
from datetime import datetime
from typing import Any, Dict

class DataAuditLogger:
    def __init__(self):
        self.logger = logging.getLogger("data_audit")

    def log_access(
        self,
        user_id: str,
        data_id: str,
        data_type: str,
        action: str,
        result: str = "success",
    ):
        """记录数据访问"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "data_access",
            "user_id": user_id,
            "data_id": data_id,
            "data_type": data_type,
            "action": action,
            "result": result,
        }

        self.logger.info(json.dumps(log_entry))

    def log_modification(
        self,
        user_id: str,
        data_id: str,
        data_type: str,
        changes: Dict[str, Any],
    ):
        """记录数据修改"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "data_modification",
            "user_id": user_id,
            "data_id": data_id,
            "data_type": data_type,
            "changes": changes,
        }

        self.logger.info(json.dumps(log_entry))

    def log_deletion(
        self,
        user_id: str,
        data_id: str,
        data_type: str,
        reason: str,
    ):
        """记录数据删除"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "data_deletion",
            "user_id": user_id,
            "data_id": data_id,
            "data_type": data_type,
            "reason": reason,
        }

        self.logger.warning(json.dumps(log_entry))
```

## 使用示例

### 综合使用

```python
# 初始化
key_manager = KeyManager()
encryption = SymmetricEncryption(key_manager.get_key("data_encryption"))
masker = DataMasker()
audit_logger = DataAuditLogger()

# 加密敏感数据
sensitive_data = {
    "user_id": "user_123",
    "email": "user@example.com",
    "ssn": "123-45-6789",
}

encrypted_data = encryption.encrypt_dict(sensitive_data, ["email", "ssn"])

# 脱敏用于日志
log_data = masker.mask_data(sensitive_data, {
    "email": "email",
    "ssn": "ssn",
})

# 记录访问
audit_logger.log_access(
    user_id="admin",
    data_id="user_123",
    data_type="user_profile",
    action="read",
)
```

## 最佳实践

### 1. 数据最小化

```python
# ✅ 好: 只收集必要的数据
def create_user(username: str, email: str):
    return {
        "username": username,
        "email": email,
        "created_at": datetime.now(),
    }

# ❌ 不好: 收集不必要的数据
def create_user(username: str, email: str, full_address: str, phone: str, ssn: str):
    # SSN 对于注册来说可能不必要
    return {
        "username": username,
        "email": email,
        "full_address": full_address,
        "phone": phone,
        "ssn": ssn,
    }
```

### 2. 加密传输

```python
# 使用 TLS/SSL
import ssl

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = True
ssl_context.verify_mode = ssl.CERT_REQUIRED
```

### 3. 安全存储

```python
# ✅ 好: 哈希密码
hashed_password, salt = DataHashing.hash_password("user_password")
db.store(user_id, password_hash=hashed_password, salt=salt)

# ❌ 不好: 明文存储
db.store(user_id, password="user_password")
```

## 相关文档

- [安全概述](overview.md) - 整体安全架构
- [认证授权](auth.md) - 访问控制
- [输入验证](input-validation.md) - 输入安全
- [输出清洗](output-sanitization.md) - 输出安全
