from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


HealthStatus = Literal[
    "operational",
    "degraded",
    "maintenance",
    "down",
    "unknown",
]

CheckStatus = Literal[
    "operational",
    "degraded",
    "down",
    "unknown",
    "not_applicable",
]


class ServiceInfo(BaseModel):
    id: str
    name: str
    version: str
    environment: str
    stack: str


class HealthCheck(BaseModel):
    status: CheckStatus
    latency_ms: float | None = None
    message: str | None = None
    metadata: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    contract_version: Literal["health.v1"] = "health.v1"
    service: ServiceInfo
    status: HealthStatus
    readiness: str | None = None
    timestamp: datetime
    uptime_seconds: int
    checks: dict[str, HealthCheck]


class LiveResponse(BaseModel):
    contract_version: Literal["health.v1"] = "health.v1"
    service_id: str
    status: Literal["alive"]
    timestamp: datetime


class ReadyResponse(BaseModel):
    contract_version: Literal["health.v1"] = "health.v1"
    service_id: str
    status: Literal["ready", "not_ready"]
    timestamp: datetime
    checks: dict[str, HealthCheck]