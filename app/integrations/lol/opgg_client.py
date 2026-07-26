"""MCP client wrapper for OP.GG's official League of Legends data server.

Connects to the officially hosted OP.GG MCP server (no API key needed, no
scraping) and exposes its tools as plain dicts in OpenAI-compatible
function-calling format, so they merge directly into the `tools` array
passed to the chat completions API. Only LoL tools are surfaced — the
server also exposes TFT and Valorant, which nobody asked for.

A fresh connection is opened per call rather than kept persistent — simple,
and fine for personal-assistant call volume.
"""

from __future__ import annotations

import logging
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

logger = logging.getLogger(__name__)

OPGG_MCP_URL = "https://mcp-api.op.gg/mcp"
TOOL_NAME_PREFIX = "lol_"


async def list_lol_tools() -> list[dict[str, Any]]:
    """Return OP.GG's LoL tools in OpenAI function-calling format."""
    async with streamablehttp_client(OPGG_MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()

    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema,
            },
        }
        for tool in result.tools
        if tool.name.startswith(TOOL_NAME_PREFIX)
    ]


async def call_lol_tool(name: str, arguments: dict[str, Any]) -> str:
    """Call an OP.GG LoL tool by name and return its text content."""
    try:
        async with streamablehttp_client(OPGG_MCP_URL) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments)
    except Exception:
        logger.exception("Failed to reach the OP.GG MCP server for tool %s", name)
        return "No pude conectar con el servidor de datos de LoL ahora mismo."

    if result.isError:
        logger.warning("OP.GG tool %s returned an error: %s", name, result.content)
        return f"El servidor de LoL devolvió un error al llamar a {name}."

    return "\n".join(block.text for block in result.content if hasattr(block, "text"))
