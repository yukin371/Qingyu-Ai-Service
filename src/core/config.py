"""
配置管理模块
使用 Pydantic Settings 从环境变量加载配置
"""
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Service
    service_name: str = Field(default="Qingyu-AI-Service", alias="SERVICE_NAME")
    service_version: str = Field(default="1.0.0", alias="SERVICE_VERSION")
    service_port: int = Field(default=8000, alias="SERVICE_PORT")
    grpc_port: int = Field(default=50051, alias="GRPC_PORT")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # OpenAI
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        alias="OPENAI_BASE_URL"
    )
    openai_model: str = Field(default="gpt-4-turbo-preview", alias="OPENAI_MODEL")

    # Anthropic
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(
        default="claude-3-sonnet-20240229",
        alias="ANTHROPIC_MODEL"
    )

    # Google Gemini
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    gemini_model: str = Field(
        default="gemini-2.0-flash-exp",
        alias="GEMINI_MODEL"
    )
    gemini_transport: str = Field(
        default="rest",
        alias="GEMINI_TRANSPORT"
    )  # rest or grpc

    # Default LLM Provider
    default_llm_provider: str = Field(
        default="gemini",
        alias="DEFAULT_LLM_PROVIDER"
    )  # openai, anthropic, gemini
    default_llm_model: str = Field(
        default="gemini-2.0-flash-exp",
        alias="DEFAULT_LLM_MODEL"
    )

    # Milvus
    milvus_host: str = Field(default="localhost", alias="MILVUS_HOST")
    milvus_port: int = Field(default=19530, alias="MILVUS_PORT")
    milvus_collection_prefix: str = Field(
        default="qingyu_ai_vectors_",
        alias="MILVUS_COLLECTION_PREFIX"
    )  # 独立前缀
    milvus_collection_name: str = Field(
        default="qingyu_knowledge",
        alias="MILVUS_COLLECTION_NAME"
    )

    # Go Backend gRPC
    go_grpc_host: str = Field(default="localhost", alias="GO_GRPC_HOST")
    go_grpc_port: int = Field(default=50051, alias="GO_GRPC_PORT")

    # Redis
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_password: str = Field(default="", alias="REDIS_PASSWORD")
    redis_key_prefix: str = Field(default="qingyu-ai:", alias="REDIS_KEY_PREFIX")  # 独立前缀
    redis_max_connections: int = Field(default=50, alias="REDIS_MAX_CONNECTIONS")

    # PostgreSQL (for Checkpointer persistence)
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_user: str = Field(default="postgres", alias="POSTGRES_USER")
    postgres_password: str = Field(default="", alias="POSTGRES_PASSWORD")
    postgres_database: str = Field(default="qingyu_ai_service", alias="POSTGRES_DATABASE")  # 独立 database

    # Checkpointer configuration
    enable_checkpointer: bool = Field(default=True, alias="ENABLE_CHECKPOINTER")
    checkpointer_backend: str = Field(
        default="postgres", alias="CHECKPOINTER_BACKEND"
    )  # postgres or redis

    # Embedding
    embedding_provider: str = Field(default="local", alias="EMBEDDING_PROVIDER")  # local, openai, custom
    embedding_model_name: str = Field(
        default="BAAI/bge-large-zh-v1.5",
        alias="EMBEDDING_MODEL_NAME"
    )
    embedding_model_device: str = Field(default="cuda", alias="EMBEDDING_MODEL_DEVICE")
    embedding_batch_size: int = Field(default=32, alias="EMBEDDING_BATCH_SIZE")
    embedding_cache_enabled: bool = Field(default=True, alias="EMBEDDING_CACHE_ENABLED")
    embedding_cache_ttl: int = Field(default=604800, alias="EMBEDDING_CACHE_TTL")  # 7天

    # OpenAI Embedding
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        alias="OPENAI_EMBEDDING_MODEL"
    )
    openai_embedding_batch_size: int = Field(default=100, alias="OPENAI_EMBEDDING_BATCH_SIZE")
    openai_embedding_max_retries: int = Field(default=3, alias="OPENAI_EMBEDDING_MAX_RETRIES")

    # Text Splitter
    text_chunk_size: int = Field(default=500, alias="TEXT_CHUNK_SIZE")
    text_chunk_overlap: int = Field(default=50, alias="TEXT_CHUNK_OVERLAP")
    text_splitter_type: str = Field(default="recursive", alias="TEXT_SPLITTER_TYPE")  # recursive, semantic

    # RAG配置
    rag_top_k: int = Field(default=5, alias="RAG_TOP_K")
    rag_rerank_top_k: int = Field(default=3, alias="RAG_RERANK_TOP_K")
    rag_max_context_tokens: int = Field(default=2000, alias="RAG_MAX_CONTEXT_TOKENS")
    rag_use_reranker: bool = Field(default=False, alias="RAG_USE_RERANKER")
    rag_use_hybrid_search: bool = Field(default=False, alias="RAG_USE_HYBRID_SEARCH")

    # Reranker配置
    reranker_model: str = Field(default="BAAI/bge-reranker-large", alias="RERANKER_MODEL")
    reranker_batch_size: int = Field(default=32, alias="RERANKER_BATCH_SIZE")

    # 混合检索配置
    hybrid_vector_weight: float = Field(default=0.7, alias="HYBRID_VECTOR_WEIGHT")
    hybrid_bm25_weight: float = Field(default=0.3, alias="HYBRID_BM25_WEIGHT")
    hybrid_fusion_method: str = Field(default="rrf", alias="HYBRID_FUSION_METHOD")  # rrf, weighted

    # 索引更新配置
    index_auto_update: bool = Field(default=True, alias="INDEX_AUTO_UPDATE")
    index_batch_size: int = Field(default=10, alias="INDEX_BATCH_SIZE")
    index_batch_interval: int = Field(default=60, alias="INDEX_BATCH_INTERVAL")  # 秒
    index_max_workers: int = Field(default=3, alias="INDEX_MAX_WORKERS")
    index_retry_times: int = Field(default=3, alias="INDEX_RETRY_TIMES")
    index_retry_delay: int = Field(default=5, alias="INDEX_RETRY_DELAY")  # 秒

    # LangSmith
    langchain_tracing_v2: bool = Field(default=False, alias="LANGCHAIN_TRACING_V2")
    langchain_endpoint: Optional[str] = Field(default=None, alias="LANGCHAIN_ENDPOINT")
    langchain_api_key: Optional[str] = Field(default=None, alias="LANGCHAIN_API_KEY")
    langchain_project: str = Field(
        default="qingyu-ai-service",
        alias="LANGCHAIN_PROJECT"
    )

    @property
    def go_grpc_address(self) -> str:
        """Go gRPC 服务地址"""
        return f"{self.go_grpc_host}:{self.go_grpc_port}"

    @property
    def milvus_uri(self) -> str:
        """Milvus 连接 URI"""
        return f"http://{self.milvus_host}:{self.milvus_port}"

    @property
    def postgres_dsn(self) -> str:
        """PostgreSQL 连接 DSN"""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
        )


# 全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取全局配置实例"""
    return settings

