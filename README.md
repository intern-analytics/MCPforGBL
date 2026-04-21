# MCP for GBL

A secure, multi-tenant Model Context Protocol (MCP) server for accessing brand-specific Postgres databases. This server supports both local execution and authenticated remote access via HTTP/SSE.

## 🔐 Authentication & Security

This server uses **Bearer Token Authentication**. Access to the `/sse` and `/messages` endpoints requires a valid API key with the `gbl-` prefix.

### 🛠️ Environment Activation
Before running any commands, ensure your virtual environment is active:

**Linux / EC2:**
```bash
source .venv/bin/activate
```

**Windows (Local):**
```powershell
.\.venv\Scripts\activate
```

### Key Management CLI
Manage your keys locally or on EC2 using the built-in auth module:

### 6. Manage Multi-Tenant API Keys (Admin API)
To provision unique database tenants to separate keys, we host an internal Admin REST API.
This API handles secrets, so it should **only** be accessed from localhost on your EC2 instance (binds to `:8001`).

### Option A: Use it securely locally via SSH Tunneling (Recommended)
You can build a secure tunnel from your Windows PC directly to your EC2 instance so you can interact with the Admin API from your own local browser (like Swagger UI) or local terminal smoothly:
```powershell
# Run this on your local Windows PC
ssh -i "path/to/your/key.pem" -L 8001:127.0.0.1:8001 ubuntu@YOUR_EC2_IP
```
Now, you can interact with the API or view the Swagger UI right from your local machine: `http://127.0.0.1:8001/docs`

### Option B: Use it directly on EC2
To start the Admin API on EC2:
```bash
python3 -m src.admin_api
```

With the Admin API running, you can create a new brand tenant key from another EC2 terminal window:
```bash
curl -X POST http://127.0.0.1:8001/keys/generate \
     -H "Content-Type: application/json" \
     -d '{"db_user": "brand_a_user", "db_pass": "supersecret"}'
```
*(The response will contain the `api_key` assigned to `brand_a_user`.)*

Other utility endpoints:
- List tenants: `curl http://127.0.0.1:8001/keys`
- Revoke tenant: `curl -X DELETE http://127.0.0.1:8001/keys/brand_a_user`

---

## 🖥️ EC2 Deployment (Persistence with systemd)

### SSH Access
To access the EC2 instance remotely:
```bash
ssh ubuntu@13.234.225.106 -i mcp_server_gbl.pem
```

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

Our platform is designed to scale securely and efficiently through a robust, role-based access control system.

We plan to scale user management by generating **separate, dedicated API keys for each user/tenant**. In our architecture, the API key acts as more than just an authentication token—it inherently defines a user's complete permission profile. The key itself tells the server exactly how much access the user has.

This approach allows us to tightly enforce database interactions and tool availability based on **limited-access accounts** and customized **skill files**, ensuring that each user only interacts with the data and capabilities they are explicitly authorized to use.

---

## 🛠️ Development

- **Local Server**: `python -m src.server` (Standard stdio)
- **SSE Server**: `python -m src.server2` (HTTP/SSE via FastAPI)
- **Auth Utils**: `src/auth.py`
- **Database Logic**: `src/db.py`
