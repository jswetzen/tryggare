"""Optional MCP wrapper over the plain tools (``mcp`` dependency group).

The assistant does not need it at runtime; it exists so the same tools can be
served to an external MCP client later.
"""

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from events.models import Event

from .tools import TOOL_NAMES, Drafts, EventTools, asyncify


def build_server(event: Event, user) -> tuple[FastMCP, Drafts]:
    tools = EventTools(event, user)
    # Masking hides unexpected exceptions; ToolError text still reaches the model.
    server = FastMCP("event-assistant", mask_error_details=True)
    for name in TOOL_NAMES:
        server.tool(asyncify(getattr(tools, name), ToolError), name=name)
    return server, tools.drafts
