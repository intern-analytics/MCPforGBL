# MCP for GBL

A secure, multi-tenant Model Context Protocol (MCP) server for accessing brand-specific Postgres databases. This server supports both local execution and authenticated remote access via HTTP/SSE.

## 🚀 Recent Updates & Enhancements (Past 10 Days)

### 🛡️ Infrastructure, Security & Scaling
- **EC2 Stabilization & Capacity Planning:** Successfully scaled the instance capacity and implemented swap memory to manage high concurrent loads. Optimized database connection pooling (`min_size=3`, `max_size=7`) to permanently resolve `ECONNREFUSED` timeout errors.
- **Enhanced Proxy & SSL:** Configured dual DuckDNS subdomains and optimized Nginx proxy settings to robustly support Server-Sent Events (SSE) for Claude connectivity with secure SSL certificate management.
- **Multi-Tenant Key Management:** Hardened the brand analytical server and configured lifecycle management for authentication across all active brand servers (Chumbak, Pepe, Cee18) to ensure consistent data reporting standards.

### 📊 Analytical Expansions (Chumbak, CEE18, Pepe)
- **Amazon SP & Advertising Data:** Integrated Amazon Seller Partner (SP) data (orders, traffic, FBA inventory). Mapped Amazon (SB/SD/SP) and Myntra CPC advertising reports into `chumbak_config.json` for granular performance insights across ad placement, product, and search-term levels.
- **Quick-Commerce Strict Segmentation:** Enforced immutable brand filters for Quick-Commerce feeds (Blinkit, Zepto, Instamart) and successfully routed Blinkit data via the DataWarehouse layer. Excluded Q-commerce D2C channels from primary sales orders to force the analytical engine to rely exclusively on dedicated raw portal feeds.
- **B2B & EBO Channel Refinement:** Updated B2B channel exclusion lists (ETRADE, R K WorldInfocom, SHANTI COSTUMES) and excluded WONDERSOFT/Mall-based EBO channels from generic `saleorders` to ensure reliance on the dedicated `ebo_sales` raw feed. Established standardized metric rules (e.g., online unit quantity as `COUNT(*)`).
- **Logistics & Offline Mappings:** 
  - Integrated **Bharatiya Mall** offline data mapping via Frangipani EBO feeds.
  - Integrated **Clickpost** logistics tracking (orders and returns).
  - Addressed POS export formatting issues with dynamic EAN/MRP column extraction.

## 📝 Brand Configuration Structure

To add a new brand to the MCP server, create a JSON file inside `src/brands/` (e.g., `brand_config.json`). The JSON file dictates the specific instructions, schema context, and access rules for the AI analyst.

**General Structure (`brand_config.json`):**
```json
{
  "brand_id": "unique_brand_identifier",
  "display_name": "Brand Business Insights",
  "tool_name": "brand_insights",
  "allowed_db_user": [
    "brand_db_user",
    "mcp_superuser"
  ],
  "description": "Short description of the AI persona and what it analyzes.",
  "specific_instructions": "[[[ PROFESSIONAL COMMUNICATION GUIDELINES ]]]\n- Instructions on persona and tone.\n\n[[[ ANALYST LOGIC & CASTING RULES ]]]\n- Date parsing, casting rules, logic exceptions.\n\n[[[ MANDATORY FILTERS ]]]\n- Rules for excluding specific channels or testing environments.\n\n[[[ PER-TABLE COLUMN REFERENCE ]]]\n- Detailed descriptions of tables, join keys, and specific column logic.",
  "schema_details": "[[[ SCHEMA OVERVIEW ]]]\n- High-level list of tables and their business purpose to help the AI write accurate SQL.",
  "common_questions": [
    "Top 10 selling SKUs for last month?",
    "Offline vs Online revenue split?"
  ]
}
```

## 🔐 Authentication & Security

This server uses **Bearer Token Authentication**. Access to the `/sse` and `/messages` endpoints requires a valid API key with the `gbl-` prefix.

### 🛠️ Environment Activation
Before running any commands, ensure your virtual environment is active:

**macOS / Linux / EC2:**
```bash
source .venv/bin/activate
```

**Windows (Local):**
```powershell
.\.venv\Scripts\activate
```

### Key Management CLI
Manage your keys locally or on EC2 using the built-in auth module:

### 6. Manage Multi-Tenant API Keys (Admin UI & API)
To provision API keys and map them to brand permissions, we host an internal Admin Dashboard and REST API. This dashboard automatically fetches the underlying database credentials from the `.env` file on the server and attaches them to an `end_user` token.

This API handles sensitive token generation, so it should **only** be accessed from localhost on your EC2 instance (binds to `:8001`).

### Option A: Access the UI securely via SSH Tunneling (Recommended)
You can build a secure tunnel from your local PC directly to your EC2 instance so you can interact with the Admin Dashboard UI in your local browser:
```powershell
# Run this on your local Windows PC
ssh -i "path/to/your/key.pem" -L 8001:127.0.0.1:8001 ubuntu@YOUR_EC2_IP
```
Now, you can interact with the UI right from your local machine: `http://127.0.0.1:8001/admin`
From the UI, you can select multiple brands at once to provision under a single end-user email! An email with the token will be automatically sent to the user.

### Option B: Use the CLI on EC2
To start the Admin API on EC2:
```bash
python3 -m src.admin_api
```

With the Admin API running, you can create a new key via a direct `curl` request:
```bash
curl -X POST http://127.0.0.1:8001/keys/generate \
     -H "Content-Type: application/json" \
     -d '{"end_user": "analyst@example.com", "brand_names": ["chumbak", "imara"]}'
```
*(The response will contain the unified `api_key` assigned to `analyst@example.com`.)*

Other utility endpoints:
- List tenants: `curl http://127.0.0.1:8001/keys`
- Revoke tenant access for a specific brand: `curl -X DELETE http://127.0.0.1:8001/keys?end_user=analyst@example.com&db_user=chumbak_user`

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

#### For Windows:
Update your `%APPDATA%\Claude\claude_desktop_config.json`. 

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

#### For macOS:
Update your `~/Library/Application Support/Claude/claude_desktop_config.json`.

```json
{
  "mcpServers": {
    "gbl-data-lake": {
      "command": "npx",
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

## 📈 Multi-Brand Scalability & Architecture

Our platform is designed to scale securely and efficiently through a unified, token-per-user model. 

Instead of an analyst managing multiple tokens for different brands, **one user receives one API key**. Within our `api_keys.json` registry, that token securely maps to any number of database credentials. At runtime, the MCP server dynamically retrieves the correct underlying database login from the EC2 `.env` file based on which tool the AI calls, ensuring rigorous multi-tenant data isolation.

## 🔄 Dual-Push GitHub Configuration

If you are migrating the codebase between organizations (e.g., from `intern-analytics` to `GOATBrandLabsTech`) but want to keep both repositories strictly synchronized from your local machine, you can configure git to push to both simultaneously with a single `git push` command.

Run these commands in your local terminal:
```bash
git remote set-url --add --push origin https://github.com/intern-analytics/MCPforGBL.git
git remote set-url --add --push origin https://github.com/GOATBrandLabsTech/MCPforGBL.git
```
Once configured, any `git push` executed locally will automatically upload your code to both organization repositories at the exact same time.

## 🛠️ Development

- **Local Server**: `python -m src.server` (Standard stdio)
- **SSE Server**: `python -m src.server2` (HTTP/SSE via FastAPI)
- **Auth Utils**: `src/auth.py`
- **Database Logic**: `src/db.py`
