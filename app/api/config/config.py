from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # General
    debug: bool = False
    serve_static: bool = True
    log_level: str = "INFO"
    log_to_file: bool = False

    # Placeholder auth (kept for compatibility with swagger config)
    aad_client_id: str = ""
    aad_tenant_id: str = ""
    aad_user_impersonation_scope_id: str = ""

    # Local storage / DB
    local_docs_dir: str = "./app/data/documents"
    sqlite_path: str = "./app/data/app.db"

    # MinerU
    mineru_base_url: str = "https://mineru.net"
    mineru_api_key: str = ""
    mineru_model_version: str = "vlm"
    mineru_poll_interval_sec: float = 1.0
    mineru_max_wait_sec: float = 300.0
    mineru_cache_artifacts: bool = True
    mineru_cache_dir: str = "./app/data/mineru"
    # MinerU bbox coordinate assumptions
    # Most MinerU JSON outputs use image-like coordinates with origin at top-left.
    mineru_bbox_origin: str = "top-left"  # "top-left" or "bottom-left"
    mineru_bbox_units: str = "auto"  # "auto", "px", "pt"
    mineru_bbox_content_coverage: float = 0.92  # used to infer full-page bbox canvas size from content extents

    # LLM (DeepSeek via LangChain)
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "chatdeepseek"

    # Streaming / batching
    pagination: int = 32

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
