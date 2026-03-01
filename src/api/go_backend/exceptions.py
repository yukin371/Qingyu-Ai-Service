"""Go后端API调用异常"""


class GoBackendError(Exception):
    """Go后端调用基础异常"""
    pass


class AuthError(GoBackendError):
    """认证失败"""
    pass


class PermissionError(GoBackendError):
    """权限不足"""
    pass


class DocumentNotFoundError(GoBackendError):
    """文档不存在"""
    pass


class ConceptNotFoundError(GoBackendError):
    """概念不存在"""
    pass


class ValidationError(GoBackendError):
    """参数验证失败"""
    pass


class APIError(GoBackendError):
    """API错误"""
    pass
