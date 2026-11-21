"""The optional MCP wrapper; skipped when the ``mcp`` dependency group is absent."""

import copy
import unittest
from unittest import mock

from asgiref.sync import async_to_sync

from events.spec_test_support import at_now

from .tests_tools import ToolsTestCase

try:
    from fastmcp import Client
    from fastmcp.exceptions import ToolError

    from .mcp_server import build_server
except ImportError:  # pragma: no cover
    build_server = None


def call(server, name, **args):
    async def run():
        async with Client(server) as client:
            return (await client.call_tool(name, args)).data

    with at_now():
        return async_to_sync(run)()


@unittest.skipIf(build_server is None, "mcp dependency group not installed")
class McpWrapperTests(ToolsTestCase):
    def test_same_tools_as_toolset(self):
        server, _ = build_server(self.event, self.staff)

        async def names():
            async with Client(server) as client:
                return {t.name for t in await client.list_tools()}

        self.assertEqual(
            async_to_sync(names)(),
            {
                "get_capabilities",
                "get_current_spec",
                "validate_spec",
                "diff_spec",
                "propose_spec",
            },
        )

    def test_propose_and_failure_text_reach_client(self):
        server, drafts = build_server(self.event, self.staff)
        spec = copy.deepcopy(self.changed_spec())
        self.assertIn(call(server, "propose_spec", spec=spec)["draft"], drafts.items)
        with self.assertRaises(ToolError) as caught:
            call(server, "propose_spec", spec={"bogus": 1})
        self.assertIn("invalid", str(caught.exception))

    def test_unexpected_errors_are_masked(self):
        def boom(self):
            raise RuntimeError("secret detail")

        with mock.patch("assistant.tools.EventTools.get_current_spec", boom):
            server, _ = build_server(self.event, self.staff)
            with self.assertRaises(ToolError) as caught:
                call(server, "get_current_spec")
        self.assertNotIn("secret detail", str(caught.exception))
