import asyncio
import sys
from mcp.server import Server
from mcp.server.stdio import stdio_server
from src.tools import register_tools

app = Server("brand-mcp-server")

# Register the tools with the server
register_tools(app)

async def main():
    async with stdio_server() as (read_stream, write_stream):
        print("Brand MCP Database Server running on stdio", file=sys.stderr)
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped.", file=sys.stderr)
