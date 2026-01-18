"""
Application Constants

This module defines application-wide constants.
"""

# =============================================================================
# Application Constants
# =============================================================================

APP_NAME = "Qingyu AI Service"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = "AI-powered service for Qingyu platform"

# =============================================================================
# API Constants
# =============================================================================

API_PREFIX = "/api/v1"
API_TITLE = "Qingyu AI Service API"
API_DESCRIPTION = "API for AI-powered services"

# =============================================================================
# Time Constants (in seconds)
# =============================================================================

DEFAULT_TIMEOUT = 30
SHORT_TIMEOUT = 5
MEDIUM_TIMEOUT = 15
LONG_TIMEOUT = 60

AGENT_EXECUTION_TIMEOUT = 300
TOOL_EXECUTION_TIMEOUT = 60
WORKFLOW_EXECUTION_TIMEOUT = 600

# =============================================================================
# Memory Constants
# =============================================================================

DEFAULT_MEMORY_LIMIT = 10000
DEFAULT_MEMORY_TTL = 86400  # 24 hours

MEMORY_TYPE_EPISODIC = "episodic"
MEMORY_TYPE_SEMANTIC = "semantic"
MEMORY_TYPE_WORKING = "working"
MEMORY_TYPE_LONG_TERM = "long_term"

# =============================================================================
# Agent Constants
# =============================================================================

DEFAULT_AGENT_TEMPERATURE = 0.7
DEFAULT_AGENT_MAX_TOKENS = 2000
DEFAULT_AGENT_MAX_ITERATIONS = 10

# =============================================================================
# Workflow Constants
# =============================================================================

DEFAULT_MAX_WORKFLOW_EXECUTION_TIME = 600
DEFAULT_WORKFLOW_RETRY_LIMIT = 3

# =============================================================================
# LLM Constants
# =============================================================================

DEFAULT_LLM_MODEL = "gpt-4"
DEFAULT_LLM_TEMPERATURE = 0.7
DEFAULT_LLM_MAX_TOKENS = 2000

# =============================================================================
# Embedding Constants
# =============================================================================

DEFAULT_EMBEDDING_MODEL = "text-embedding-ada-002"
DEFAULT_EMBEDDING_DIMENSIONS = 1536

# =============================================================================
# Vector Database Constants
# =============================================================================

DEFAULT_VECTOR_INDEX = "qingyu"
DEFAULT_VECTOR_METRIC = "cosine"
DEFAULT_EF_CONSTRUCTION = 200
DEFAULT_M = 16

# =============================================================================
# Pagination Constants
# =============================================================================

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# =============================================================================
# File Size Constants (in bytes)
# =============================================================================

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
MAX_DOCUMENT_SIZE = 5 * 1024 * 1024  # 5MB

# =============================================================================
# Rate Limiting Constants
# =============================================================================

DEFAULT_RATE_LIMIT = 100  # requests per minute
STRICT_RATE_LIMIT = 10  # requests per minute

# =============================================================================
# Status Codes
# =============================================================================

STATUS_SUCCESS = "success"
STATUS_ERROR = "error"
STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"

# =============================================================================
# Error Messages
# =============================================================================

ERROR_NOT_FOUND = "Resource not found"
ERROR_VALIDATION = "Validation failed"
ERROR_AUTHENTICATION = "Authentication failed"
ERROR_AUTHORIZATION = "Authorization failed"
ERROR_RATE_LIMIT = "Rate limit exceeded"
ERROR_SERVER = "Internal server error"

# =============================================================================
# Feature Flags
# =============================================================================

FEATURE_LANGCHAIN_TRACING = "langchain_tracing"
FEATURE_EMBEDDINGS = "embeddings"
FEATURE_VECTOR_SEARCH = "vector_search"
FEATURE_WORKFLOWS = "workflows"
FEATURE_MULTI_MODAL = "multi_modal"

# =============================================================================
# Environment Names
# =============================================================================

ENV_DEVELOPMENT = "development"
ENV_TESTING = "testing"
ENV_STAGING = "staging"
ENV_PRODUCTION = "production"

# =============================================================================
# Log Levels
# =============================================================================

LOG_DEBUG = "DEBUG"
LOG_INFO = "INFO"
LOG_WARNING = "WARNING"
LOG_ERROR = "ERROR"
LOG_CRITICAL = "CRITICAL"

# =============================================================================
# Reserved Names
# =============================================================================

RESERVED_USER_NAMES = ["admin", "system", "root"]
RESERVED_AGENT_NAMES = ["system", "default"]
