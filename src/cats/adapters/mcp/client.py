from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Mapping, Protocol


class MCPToolClient(Protocol):
    """Minimal CATS-facing MCP tool client boundary.

    CATS components depend on this narrow contract rather than on the MCP SDK.
    Implementations may use stdio, HTTP, or another MCP transport.
    """

    def call_tool(self, name: str, arguments: Mapping[str, Any]) -> Any:
        ...


@dataclass(frozen=True)
class StdioMCPServerConfig:
    command: str
    args: tuple[str, ...] = ()
    env: Mapping[str, str] | None = None


class StdioMCPToolClient:
    """Official-SDK MCP client for latency-tolerant CATS capabilities.

    The SDK is loaded lazily so core CATS V2ET tests do not require the optional
    MCP dependency. Each client is configured with an explicit allow-list;
    MCP capability discovery never grants CATS authority by itself.

    This first V2ET implementation opens a fresh stdio session for each tool
    call. That is intentionally simple and appropriate for the initial
    functional experiment, but its timing must not be generalized to a
    persistent MCP session without separate measurement.
    """

    def __init__(
        self,
        server: StdioMCPServerConfig,
        *,
        allowed_tools: frozenset[str] | None = None,
    ):
        self.server = server
        self.allowed_tools = allowed_tools

    def call_tool(self, name: str, arguments: Mapping[str, Any]) -> Any:
        if self.allowed_tools is not None and name not in self.allowed_tools:
            raise PermissionError(f"MCP tool is not authorized for this CATS connector: {name}")
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._call_tool(name, dict(arguments)))
        raise RuntimeError(
            "StdioMCPToolClient.call_tool() is synchronous and cannot run inside an active "
            "asyncio event loop. Use it from the current synchronous CATS runtime or add an "
            "async connector implementation."
        )

    async def _call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError as exc:  # pragma: no cover - depends on optional package
            raise RuntimeError(
                'MCP support is optional. Install it with: pip install -e ".[mcp]"'
            ) from exc

        params = StdioServerParameters(
            command=self.server.command,
            args=list(self.server.args),
            env=None if self.server.env is None else dict(self.server.env),
        )
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments)
        return self._normalize_result(result)

    @staticmethod
    def _normalize_result(result: Any) -> Any:
        structured = getattr(result, "structuredContent", None)
        if structured is None:
            structured = getattr(result, "structured_content", None)
        if structured is not None:
            return structured

        content = getattr(result, "content", None) or []
        if not content:
            return None
        first = content[0]
        text = getattr(first, "text", None)
        if text is None:
            return first
        try:
            return json.loads(text)
        except (TypeError, json.JSONDecodeError):
            return text
