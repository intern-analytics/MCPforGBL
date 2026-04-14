---
theme: default
class: text-center
---

# 🚀 Unlocking the GBL Data Lake
## Integrating AI with the Model Context Protocol (MCP)

---

# 🧠 What is an MCP?

The **Model Context Protocol (MCP)** is an open-source standard introduced by Anthropic. 

Think of it like a **"USB-C port for AI applications."**
- It securely connects AI models (like Claude) to external data sources.
- Instead of uploading sensitive data or giving AI direct internet access, the AI talks to a secure, standardized API.
- The MCP Server defines **tools** that the AI can call to read data on-demand.

---

# 🏢 Why do we need an MCP for GBL?

We have massive amounts of valuable data sitting in our internal PostgreSQL databases. 

**The Goal:** Empower our team to use Claude to analyze Data Lake information instantly without writing SQL.

**The Problem:** We cannot securely give Claude.ai our raw database credentials.

**The Solution:** We built a custom **Brand MCP Server**. 
Claude talks to our MCP Server, and our MCP Server securely fetches data from the database on Claude's behalf. We maintain 100% control over the data flow.

---

# 🏗️ System Architecture

Our MCP server is deployed remotely for maximum security and availability.

1. **The Client:** A team member opens Claude.ai in their web browser.
2. **The Connection (SSE):** Claude connects to our remote server via a live Server-Sent Events (SSE) stream over HTTPS (`mcpforgbl.duckdns.org`).
3. **The Gateway:** Nginx receives the secure request and proxies it to our FastAPI Python application on AWS EC2.
4. **The Database:** Our Python app validates the request, executes the read-only query against the GBL Postgres Database, and returns the data back to Claude.

---

# 🔒 Security & Multi-Tenancy

We built this from the ground up to support multiple brands securely:

- **Strict Access Control:** Every connection requires a highly secure `Bearer Token` API Key (e.g., `gbl-xyz123`). 
- **Revocation:** If a key is compromised, or a vendor leaves, we can instantly revoke their specific key via our CLI without affecting anyone else.
- **Data Scoping:** The infrastructure is prepared for multi-tenancy. Using the API key, the server identifies the user and will auto-inject filters (like `WHERE brand_id = X`) to ensure isolated data access.
- **Read-Only:** The database user given to the MCP server strictly only possesses `SELECT` permissions.

---

# 🛠️ What Can Claude Do?

We have currently equipped our MCP server with specific skills/tools that Claude can automatically trigger:

* 🗄️ **`list_tables`**: Claude can dynamically ask the database what tables and schemas are currently available to explore.
* ⚡ **`execute_query`**: Claude can write and execute PostgreSQL queries to extract precisely the data it needs to answer your business questions, perform math, and create charts on the fly.

---

# 🚀 How to Set It Up & Use It

We have successfully opened the remote connection! Anyone on the team with an API Key can start using it immediately:

### Step 1: Get an API Key
Request an API key from the engineering team. It will look like `gbl-...`.

### Step 2: Connect Claude.ai
- Open **Claude.ai** and navigate to your Settings -> **Connectors**.
- Click **Add custom connector**.
- Paste our secure server URL and append your key: 
  `https://mcpforgbl.duckdns.org/sse?token=gbl-YOUR_KEY_HERE`

### Step 3: Analyze Data
Start chatting! Try asking Claude: *"Please use your tools to check what tables we have in the database, and tell me our highest performing metrics."*

---

# 🗺️ Future Roadmap

Where do we go from here?

1. **Admin Dashboard UI:** We are building a premium graphical dashboard (glassmorphic dark-mode web app) so non-technical managers can generate and revoke API keys visually at `https://tejas-something.com`.
2. **Complex Tools:** Expanding the toolset so Claude doesn't have to write raw SQL, but can use pre-approved endpoints like `get_brand_sales_report(brand_name)`.
3. **Audit Logging:** Integrating dashboards to monitor exactly which AI queries are consuming the most resources and track database utilization.
