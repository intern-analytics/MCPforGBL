# MCP for GBL

A secure, multi-tenant Model Context Protocol (MCP) server for accessing brand-specific Postgres databases. This server supports both local execution and authenticated remote access via HTTP/SSE.

## 🔐 Authentication & Security

This server uses **Bearer Token Authentication**. Access to the `/sse` and `/messages` endpoints requires a valid API key with the `gbl-` prefix.

### Key Management CLI
Manage your keys locally or on EC2 using the built-in auth module:

```bash
# Activate your environment first
source .venv/bin/activate  # Linux/EC2
.\.venv\Scripts\activate   # Windows

# Generate a new key for a brand
python -m src.auth generate "Chumbak"

# List all active brands and keys
python -m src.auth list

# Revoke access for a brand
python -m src.auth revoke "OldBrand"
```

---

## 🖥️ EC2 Deployment (Persistence with systemd)

For production, we use `systemd` to ensure the server starts automatically on reboot and restarts if it crashes.

### 1. Project Setup
```bash
git clone https://github.com/intern-analytics/MCPforGBL.git
cd MCPforGBL
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuration
Create a `.env` file for database credentials (gitignored):
```bash
nano .env
# Add DB_USER, DB_PASS, DB_HOST, etc.
```

### 3. Create the System Service
Create a service file:
```bash
sudo nano /etc/systemd/system/mcp-server.service
```
Paste the following (adjust paths if necessary):
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

### 4. Enable and Start
```bash
sudo systemctl daemon-reload
sudo systemctl enable mcp-server
sudo systemctl start mcp-server
sudo systemctl status mcp-server
```

---

## 🤖 Connecting to Claude

### Option A: Using Claude.ai (Web App)
Because this server is publicly exposed via Nginx and protected with a Let's Encrypt HTTPS certificate, you can connect directly in your browser.

1. Go to Claude.ai Settings -> **Developer** / **Connectors**.
2. Click **Add custom connector**.
3. Paste your secure URL: `https://mcpforgbl.duckdns.org/sse?token=gbl-YOUR_KEY_HERE`
4. Connect and query!

### Option B: Using Claude Desktop App (HTTPS)
Update your `%APPDATA%\Claude\claude_desktop_config.json` on Windows. 

> [!IMPORTANT]  
> Use `C:\\PROGRA~1\\nodejs\\npx.cmd` to avoid issues with spaces in the Windows file path.

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

### Option C: Using Claude Desktop App (HTTP IP Address & Bearer Header)
If you prefer to connect directly to the EC2 instance's IP without using the DuckDNS URL or want to pass the token as a header instead of a URL parameter, use this configuration:

```json
{
  "mcpServers": {
    "gbl-data-lake": {
      "command": "C:\\PROGRA~1\\nodejs\\npx.cmd",
      "args": [
        "-y",
        "mcp-remote",
        "http://YOUR-EC2-PUBLIC-IP:8000/sse",
        "--allow-http",
        "--header",
        "Authorization: Bearer gbl-YOUR_KEY_HERE"
      ]
    }
  }
}
```

---

## 📈 Scalability Roadmap

The server is architected to support multiple brands under one deployment:
- **Key-Based Context**: Mapping API keys to specific brand column filters.
- **Query Scoping**: Auto-injecting `WHERE brand_id = '...'` into all incoming queries.
- **Audit Logs**: Access logging located in `access.log` to monitor which brands are querying at what time.

---

## 🛠️ Development

- **Local Server**: `python -m src.server` (Standard stdio)
- **SSE Server**: `python -m src.server2` (HTTP/SSE via FastAPI)
- **Auth Utils**: `src/auth.py`
- **Database Logic**: `src/db.py`
