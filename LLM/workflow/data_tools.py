"""
Data Analysis Tools for Agent Workflow

This module provides MCPToolset integration for the data analyst agent to query
indicators data via the MCP server running in the service container.

All data access is done through MCP tools - no direct imports from service/ directory.
"""
import logging
import warnings

# Suppress the UserWarning about experimental features
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message=".*BaseAuthenticatedTool: This feature is experimental.*"
)

from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, SseConnectionParams

# Suppress the logging WARNING about missing auth_config
logging.getLogger("google_adk.google.adk.tools").setLevel(logging.ERROR)


from common import MCP_SERVER_URL


def create_mcp_toolset() -> MCPToolset:
    """
    Create an MCPToolset configured to connect to the SenegalMEG MCP server.

    Returns:
        MCPToolset configured for SSE connection to the indicators data server.

    Raises:
        RuntimeError: If MCPToolset creation fails.
    """
    try:
        # Create MCPToolset with SSE connection to the remote MCP server
        toolset = MCPToolset(
            connection_params=SseConnectionParams(
                url=MCP_SERVER_URL,
                headers=None,  # No auth headers for local dev server,
                # Add authentication headers if needed in production
                # headers={"Authorization": "Bearer your-token"}
            ),
        )
        return toolset
    except Exception as e:
        raise RuntimeError(f"Failed to create MCPToolset: {e}") from e
