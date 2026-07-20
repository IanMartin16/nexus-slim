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


router = APIRouter(prefix="/api/health", tags=["health"])


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@router.get(
    "",
    response_model=HealthResponse,
)
async def health(response: Response) -> HealthResponse:
    response.status_code = status.HTTP_200_OK

    return HealthResponse(
        service=ServiceInfo(
            id="nexus-slim",
            name="Nexus Slim",
            version=settings.APP_VERSION,
            environment=settings.ENVIRONMENT,
            stack="fastapi",
        ),
        status="operational",
        readiness="ready",
        timestamp=utc_now(),
        uptime_seconds=get_uptime_seconds(),
        checks={
            "application": HealthCheck(
                status="operational",
            ),
            "configuration": HealthCheck(
                status="operational",
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
    response.status_code = status.HTTP_200_OK

    return ReadyResponse(
        service_id="nexus-slim",
        status="ready",
        timestamp=utc_now(),
        checks={
            "configuration": HealthCheck(
                status="operational",
            ),
        },
    )