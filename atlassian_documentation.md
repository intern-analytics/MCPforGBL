# MCP for GBL

## Overview
This document provide the setup, configuration, and architectural details for the **MCP for GBL** Server. The server provides Claude with secure access to the GBL Postgres database. It runs remotely as a FastAPI background service and exposes an authenticated HTTP/SSE (Server-Sent Events) endpoint.

---

## 🔒 Security & Authentication
The server implements **Bearer Token Authentication** to ensure only authorized clients can interact with the database.

### Key Management (Admin API)
Admins manage tenant access using the local REST API running on port `8001`.
- **Start API**: `python3 -m src.admin_api` (binds strictly to localhost)
- **Generate Key**: `curl -X POST http://127.0.0.1:8001/keys/generate -H "Content-Type: application/json" -d '{"db_user": "tenant_user", "db_pass": "pass"}'`
- **Revoke Key**: `curl -X DELETE http://127.0.0.1:8001/keys/tenant_user`

Keys are stored in `api_keys.json` (gitignored). The system dynamically instantiates isolated PostgreSQL connection pools tied exactly to the `db_user` attached to the requested key.

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
    # Authenticates and locks session logic securely
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())

# Hosted as an ASGI app wrapper to natively support Session extraction from Claude Web requests dropping URL query parameters.
fastapi_app.mount("/messages", custom_messages_app)
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

## 💻 Connecting to Claude

### Via Claude.ai (Web App)
1. Navigate to Settings -> **Connectors**.
2. Click **Add custom connector**.
3. Input Server URL: `https://mcpforgbl.duckdns.org/sse?token=gbl-YOUR_KEY_HERE`

### Via Claude Desktop Config
Users must use the `mcp-remote` proxy.

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
        "https://mcpforgbl.duckdns.org/sse?token=gbl-YOUR_KEY_HERE"
      ]
    }
  }
}
```
