from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # LLM — provider prefix convention: openai/ routes to any OpenAI-compatible API
    # (e.g. vLLM at llm_api_base), anthropic/ to Anthropic, vertex_ai/ to Vertex AI.
    llm_model: str = "openai/qwen2.5-0.5B-Instruct"
    llm_api_base: str | None = None
    llm_api_key: str | None = None

    # OpenTelemetry (used in Phase 4)
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "react-medical-triage"


settings = Settings()
