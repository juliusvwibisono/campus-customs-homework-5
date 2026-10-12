"""The only shop-data boundary used by the agent team."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastmcp import Client


class MCPGateway:
    """Connect to the local MCP server and never open the SQLite file directly."""

    def __init__(self, project_root: Path):
        self.server_path = project_root / "mcp_server" / "server.py"
        self.client: Client | None = None

    async def __aenter__(self) -> "MCPGateway":
        self.client = Client(self.server_path)
        await self.client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        if self.client is not None:
            await self.client.__aexit__(exc_type, exc_value, traceback)
            self.client = None

    async def call(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
        if self.client is None:
            raise RuntimeError("MCPGateway must be used inside an async context")
        result = await self.client.call_tool(tool_name, arguments or {})
        if getattr(result, "is_error", False):
            raise RuntimeError(f"MCP tool {tool_name} returned an error: {result}")

        data = getattr(result, "data", None)
        if data is not None:
            return data
        structured = getattr(result, "structured_content", None)
        if structured is not None:
            if isinstance(structured, dict) and set(structured) == {"result"}:
                return structured["result"]
            return structured
        content = getattr(result, "content", [])
        texts = [getattr(item, "text", str(item)) for item in content]
        if len(texts) == 1:
            try:
                return json.loads(texts[0])
            except json.JSONDecodeError:
                return texts[0]
        return texts
