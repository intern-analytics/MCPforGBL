import asyncio
import sys
import os
from mcp.server import Server
from mcp.server.stdio import stdio_server
from src.tools import register_tools
from src.auth import authorized_brands_var, load_keys, _migrate_key_to_brands
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

app = Server("brand-mcp-server")

# Register the tools with the server
register_tools(app)

async def main():
    # Authenticate via API_KEY
    api_key = os.getenv("API_KEY")
    if not api_key:
        print("Error: API_KEY environment variable is required.", file=sys.stderr)
        sys.exit(1)
        
    keys = load_keys()
    key_data = keys.get(api_key)
    
    if not key_data or not isinstance(key_data, dict):
        print("Error: Invalid API Key.", file=sys.stderr)
        sys.exit(1)
        
    now = datetime.now(timezone.utc)
    expires_at_str = key_data.get("expires_at")
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if now > expires_at:
                print("Error: API Key Expired. Please revalidate.", file=sys.stderr)
                sys.exit(1)
        except ValueError:
            pass

    # Ensure nested format exists
    key_data = _migrate_key_to_brands(key_data)

    # Set context variables for the database credentials mapped to this key
    authorized_brands_var.set(key_data.get("brands", {}))

    async with stdio_server() as (read_stream, write_stream):
        print("Brand MCP Database Server running on stdio", file=sys.stderr)
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped.", file=sys.stderr)
