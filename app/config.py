"""config.py — settings del servicio. Todo por entorno (prefijo NEXUS_)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "nexus-slim"
    version: str = "1.0"

    # Salida hacia el cerebro vía evi-gateway (proxy con sobre route+payload).
    gateway_url: str = "http://localhost:8080"
    gateway_proxy_path: str = "/api/proxy"
    gateway_api_key: str = "nexus_dev_key"
    gateway_mcpone_route: str = "mcpone.execute"
    request_timeout_s: float = 60.0

    # Desarrollo local sin MCPOne: emite la secuencia mock del cliente.
    mock_brain: bool = False

    MCPONE_BASE_URL: str = "https://mcp-one-production.up.railway.app"
    APP_VERSION: str = "1.0"
    ENVIRONMENT: str = "development"

    # CORS para el widget montado en el portal.
    cors_origins: list[str] = ["*"]

    model_config = SettingsConfigDict(env_prefix="NEXUS_", env_file=".env", extra="ignore", case_sensitive=False)


settings = Settings()
