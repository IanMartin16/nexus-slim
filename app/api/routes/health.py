from datetime import datetime, timezone

from fastapi import APIRouter, Response, status

from app.config import settings
from app.core.runtime import get_uptime_seconds
from app.models.health import (
    HealthCheck,
    HealthResponse,
    LiveResponse,
    ReadyResponse,
    ServiceInfo,
)
from app.services.mcpone_health import MCPOneHealthClient


router = APIRouter(prefix="/api/health", tags=["health"])

mcpone_client = MCPOneHealthClient(
    base_url=settings.MCPONE_BASE_URL,
    timeout_seconds=2.0,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@router.get(
    "",
    response_model=HealthResponse,
)
async def health(response: Response) -> HealthResponse:
    mcpone_status, latency_ms, message = (
        await mcpone_client.check_readiness()
    )

    overall_status = (
        "operational"
        if mcpone_status == "operational"
        else "degraded"
    )

    response.status_code = status.HTTP_200_OK

    return HealthResponse(
        service=ServiceInfo(
            id="nexus-slim",
            name="Nexus Slim",
            version=settings.APP_VERSION,
            environment=settings.ENVIRONMENT,
            stack="fastapi",
        ),
        status=overall_status,
        timestamp=utc_now(),
        uptime_seconds=get_uptime_seconds(),
        checks={
            "application": HealthCheck(
                status="operational",
            ),
            "configuration": HealthCheck(
                status="operational",
            ),
            "mcpone": HealthCheck(
                status=mcpone_status,
                latency_ms=latency_ms,
                message=message,
            ),
        },
    )


@router.get(
    "/live",
    response_model=LiveResponse,
)
async def live() -> LiveResponse:
    return LiveResponse(
        service_id="nexus-slim",
        status="alive",
        timestamp=utc_now(),
    )


@router.get(
    "/ready",
    response_model=ReadyResponse,
)
async def ready(response: Response) -> ReadyResponse:
    mcpone_status, latency_ms, message = (
        await mcpone_client.check_readiness()
    )

    is_ready = mcpone_status == "operational"

    response.status_code = (
        status.HTTP_200_OK
        if is_ready
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return ReadyResponse(
        service_id="nexus-slim",
        status="ready" if is_ready else "not_ready",
        timestamp=utc_now(),
        checks={
            "configuration": HealthCheck(
                status="operational",
            ),
            "mcpone": HealthCheck(
                status=mcpone_status,
                latency_ms=latency_ms,
                message=message,
            ),
        },
    )