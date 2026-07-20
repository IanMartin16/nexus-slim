from time import perf_counter

import httpx


class MCPOneHealthClient:
    def __init__(self, base_url: str, timeout_seconds: float = 2.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def check_readiness(self) -> tuple[str, float | None, str | None]:
        started_at = perf_counter()

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(
                    f"{self.base_url}/health"
                )

            latency_ms = round((perf_counter() - started_at) * 1000, 2)

            if response.status_code == 200:
                payload = response.json()

                if payload.get("status") == "ready":
                    return "operational", latency_ms, None

                return "degraded", latency_ms, "MCPOne is not ready"

            return (
                "down",
                latency_ms,
                f"MCPOne readiness returned HTTP {response.status_code}",
            )

        except httpx.TimeoutException:
            latency_ms = round((perf_counter() - started_at) * 1000, 2)
            return "down", latency_ms, "MCPOne readiness timed out"

        except httpx.HTTPError as exc:
            latency_ms = round((perf_counter() - started_at) * 1000, 2)
            return "down", latency_ms, f"MCPOne health request failed: {exc}"