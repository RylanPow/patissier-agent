import sys
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List
from langchain_core.tools import BaseTool

from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession
from langchain_mcp_adapters.tools import load_mcp_tools

# use the current python executable to run the server script
SERVER_SCRIPT = os.path.join(os.getcwd(), "mcp_server", "server.py")

server_params = StdioServerParameters(
    command=sys.executable,
    args = [SERVER_SCRIPT],
    env = os.environ.copy()
)
@asynccontextmanager
async def get_mcp_tools() -> AsyncGenerator[List[BaseTool], None]:
    """
    Spawns the FastMCP server as a subprocess, initializes the JSON RPC session, 
    and returns a list of LangChain compatible tols.
    """ 
    # start the subprocess and connect via stdio
    async with stdio_client(server_params) as (read_stream, write_stream):
        #open an MCP session over those streams
        async with ClientSession(read_stream, write_stream) as session:
            # complete the MCP handshake
            await session.initialize()
            # convert MCP tools to LangChain tools
            tools = await load_mcp_tools(session)
            # yield the tools to the caller (the server stays alive during this yield)
            yield tools