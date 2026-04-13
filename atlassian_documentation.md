# Brand MCP Server Documentation (GBL Data Lake)

## Overview
This document provide the setup, configuration, and architectural details for the **MCP for GBL** Server. The server provides Claude with secure access to the GBL Postgres database. It runs remotely as a FastAPI background service and exposes an authenticated HTTP/SSE (Server-Sent Events) endpoint.

---

## 🔒 Security & Authentication
The server implements **Bearer Token Authentication** to ensure only authorized clients can interact with the database.

### Key Management
Admins can manage access keys using the `src/auth.py` utility:
- **Generate Key**: `python -m src.auth generate "BrandName"`
- **List Keys**: `python -m src.auth list`
- **Revoke Key**: `python -m src.auth revoke "BrandName"`

Keys are stored in `api_keys.json` (gitignored for security) and use the `gbl-` prefix.

---

## 🏗️ Architecture

### Core Server (`src/server2.py`)
The server uses FastAPI to wrap the MCP protocol. Every sensitive endpoint is protected by the `verify_api_key` dependency.

```python
from fastapi import FastAPI, Request, Depends
from src.auth import verify_api_key
from mcp.server import Server
from mcp.server.sse import SseServerTransport

app = Server("brand-mcp-server")
register_tools(app)
sse = SseServerTransport("/messages")
fastapi_app = FastAPI(title="Brand MCP HTTP/SSE Server")

@fastapi_app.get("/sse")
async def handle_sse(request: Request, token: str = Depends(verify_api_key)):
    async with sse.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

@fastapi_app.post("/messages")
async def handle_messages(request: Request, token: str = Depends(verify_api_key)):
    await sse.handle_post_message(request.scope, request.receive, request._send)
```

---

## 🚀 EC2 Deployment (Persistence)

To ensure the server stays running 24/7 on Ubuntu, we use a `systemd` service.

1. **Path**: `/etc/systemd/system/mcp-server.service`
2. **Service Definition**:
```ini
[Unit]
Description=Brand MCP FastAPI Server
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/projects/MCPforGBL
ExecStart=/home/ubuntu/projects/MCPforGBL/.venv/bin/python -m src.server2
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

3. **Commands**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable mcp-server
sudo systemctl start mcp-server
```

---

## 💻 Claude Desktop Configuration
Users must use the `mcp-remote` proxy with the correct headers.

> [!IMPORTANT]
> To avoid Windows path errors with `cmd.exe`, use the short-path `C:\\PROGRA~1\\nodejs\\npx.cmd`.

```json
{
  "mcpServers": {
    "gbl-data-lake": {
      "command": "C:\\PROGRA~1\\nodejs\\npx.cmd",
      "args": [
        "-y",
        "mcp-remote",
        "http://YOUR-EC2-IP:8000/sse",
        "--allow-http",
        "--header",
        "Authorization: Bearer gbl-YOUR_KEY_HERE"
      ]
    }
  }
}
```
