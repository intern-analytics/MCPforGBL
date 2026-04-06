# Brand MCP Server Documentation

## Overview
This document provides the complete setup, configuration, and architectural details for the Brand MCP (Model Context Protocol) Server. The server provides Claude with secure access to the Brand Postgres database. It runs remotely as a FastAPI background service and exposes an HTTP/SSE (Server-Sent Events) endpoint, avoiding the need to share SSH keys directly with end-users.

---

## Architecture & Code Snippets

The core of the server uses FastAPI to handle standard HTTP requests and SSE for real-time messages.

### Core Server Implementation (`src/server2.py`)
This is the main entry point that initializes the MCP Server and connects it to the FastAPI routes.

```python
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mcp.server import Server
from mcp.server.sse import SseServerTransport
import uvicorn

# Import the existing tool registration from your src directory
from src.tools import register_tools

# Create the MCP server instance
app = Server("brand-mcp-server")

# Register your existing tools with the server
register_tools(app)

# Initialize the SSE transport and tell it where POST messages will arrive
sse = SseServerTransport("/messages")

# Build the FastAPI application
fastapi_app = FastAPI(title="Brand MCP HTTP/SSE Server")

@fastapi_app.get("/")
async def root():
    """A simple root endpoint to verify the server is running."""
    return JSONResponse({"status": "brand-mcp-server running directly on FastAPI HTTP/SSE"})

@fastapi_app.get("/sse")
async def handle_sse(request: Request):
    """The main Server-Sent Events endpoint for MCP clients."""
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as (read_stream, write_stream):
        await app.run(
            read_stream, write_stream, app.create_initialization_options()
        )

@fastapi_app.post("/messages")
async def handle_messages(request: Request):
    """Endpoint for MCP clients to POST incoming messages."""
    await sse.handle_post_message(request.scope, request.receive, request._send)

if __name__ == "__main__":
    print("Starting Brand MCP SSE Server on http://0.0.0.0:8000")
    uvicorn.run("src.server2:fastapi_app", host="0.0.0.0", port=8000, reload=True)
```

---

## EC2 Deployment Instructions (Ubuntu Server)

These are the instructions to deploy the Python server on your remote EC2 Environment.

1. **Update System & Install Global Dependencies**
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install git python3 python3-pip python3-venv -y
   ```

2. **Clone the Project Repository**
   ```bash
   git clone https://github.com/MiKecantdothis/MCPforGBL.git
   cd MCPforGBL
   ```

3. **Set Up Python Environment and Packages**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Environment Variables Config (`.env`)**
   Since `.env` is omitted from version control, create it directly on the server:
   ```bash
   nano .env
   ```
   *Fill in your required database variables (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASS`).*

5. **Run the Server in the Background**
   Start the FastAPI app securely in the background using `nohup`:
   ```bash
   nohup python3 -m src.server2 > server.log 2>&1 &
   ```
   *Ensure your EC2 Security Groups allow Inbound TCP traffic on **Port 8000**.*

---

## Claude Desktop Configuration (End-User Setup)

To connect Claude Desktop to the active server, users need to utilize the `mcp-remote` NPX package to establish the remote SSE connection.

> **Note on Windows Environments**: If the `npx.cmd` path configuration fails to launch (e.g., Claude simply says it is "not working"), this is often a limitation of how Claude's underlying Node process spawns `.cmd` executables. The best workaround is to invoke `cmd.exe` directly.

### Standard Configuration Provided
*(Add the following to `%APPDATA%\Claude\claude_desktop_config.json`)*
```json
{
  "mcpServers": {
    "brand-db-free-access": {
      "command": "C:\\Program Files\\nodejs\\npx.cmd",
      "args": [
        "-y",
        "mcp-remote",
        "http://13.234.225.106:8000/sse",
        "--allow-http"
      ]
    }
  },
  "preferences": {
    "menuBarEnabled": false,
    "coworkScheduledTasksEnabled": true,
    "ccdScheduledTasksEnabled": true,
    "sidebarMode": "chat",
    "coworkWebSearchEnabled": false
  }
}
```

### Alternative Configuration (Recommended for Windows Fix)
If the above configuration fails on Windows, use the `cmd.exe` approach so the system shell evaluates the `npx` command properly:

```json
{
  "mcpServers": {
    "brand-db-free-access": {
      "command": "cmd.exe",
      "args": [
        "/c",
        "npx",
        "-y",
        "mcp-remote",
        "http://13.234.225.106:8000/sse",
        "--allow-http"
      ]
    }
  }
}
```
