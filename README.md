# Brand MCP Server (Python)

This provides an MCP server for accessing the brand Postgres database using Python.

## Setup Instructions

1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   # Windows
   .venv\\Scripts\\activate
   pip install -r requirements.txt
   ```

2. Configure environment:
   Copy `.env.example` to `.env` and fill in your database credentials:
   ```bash
   cp .env.example .env
   ```

3. Claude Desktop Configuration:
   Add this to your `claude_desktop_config.json`:
   ```json
   {
     "mcpServers": {
       "brand-db": {
         "command": "C:\\Users\\Mike\\Desktop\\Chumbak MCP\\brand-mcp-server\\.venv\\Scripts\\python.exe",
         "args": ["-m", "src.server"],
         "env": {
           "DB_HOST": "localhost",
           "DB_PORT": "5432",
           "DB_NAME": "brand_db",
           "DB_USER": "postgres",
           "DB_PASS": "password",
           "PYTHONPATH": "C:\\Users\\Mike\\Desktop\\Chumbak MCP\\brand-mcp-server"
         }
       }
     }
   }
   ```
