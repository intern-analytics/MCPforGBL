import asyncio
import sys
import os
from mcp.server import Server
from mcp.server.stdio import stdio_server
from src.tools import register_tools
from src.auth import db_user_var, db_pass_var
from dotenv import load_dotenv

load_dotenv()

app = Server("brand-mcp-server")

# Register the tools with the server
register_tools(app)

async def main():
    # Set context variables for local testing using environment variables
    # This identifies the session as 'chumbak_mcp' (or whatever is in your .env)
    db_user_var.set(os.getenv("DB_USER"))
    db_pass_var.set(os.getenv("DB_PASS"))

    async with stdio_server() as (read_stream, write_stream):
        print("Brand MCP Database Server running on stdio", file=sys.stderr)
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped.", file=sys.stderr)
