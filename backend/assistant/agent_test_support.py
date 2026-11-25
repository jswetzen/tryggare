"""Stand-in tools for agent tests (a name test discovery does not match)."""

from pydantic_ai import ModelRetry
from pydantic_ai.toolsets import FunctionToolset


def stand_in_toolset() -> FunctionToolset:
    """Tiny tools that fail on bad input, to exercise tool errors and retries."""
    state: dict = {}
    toolset = FunctionToolset()

    @toolset.tool_plain
    def get_capabilities() -> dict:
        """List the event fields the assistant may set."""
        return {"fields": ["name", "start_date"], "unsupported": ["custom form fields"]}

    @toolset.tool_plain
    def set_event_name(name: str) -> str:
        """Set the event name. Must not be empty."""
        if not name.strip():
            raise ModelRetry("name must not be empty")
        state["name"] = name
        return f"name set to {name!r}"

    return toolset
