"""
smoke.py — prueba el multiplex SSE sin levantar servidor ni MCPOne.

Ejercita composer.stream_chat con el cliente del cerebro en modo mock e imprime
el stream SSE crudo. Sirve para validar que entrada (neutral) -> salida (sections)
funciona end-to-end.

Uso:  python -m scripts.smoke   (desde la raíz del repo)
"""

import asyncio

import httpx

from app.clients.mcpone import MCPOneClient
from app.config import Settings
from app.core import composer


async def main() -> None:
    settings = Settings(mock_brain=True)
    async with httpx.AsyncClient() as http:
        brain = MCPOneClient(http, settings)
        async for frame in composer.stream_chat(brain, "¿cómo está el mercado?", "sess_demo"):
            print(frame.decode("utf-8"), end="")


if __name__ == "__main__":
    asyncio.run(main())
