# MCP for GBL

This provides an MCP server for accessing the brand Postgres database using Python.

## Setup Instructions (Local)

1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Configure environment:
   Copy `.env.example` to `.env` and fill in your database credentials:
   ```bash
   cp .env.example .env
   ```

3. Claude Desktop Configuration:
   On Windows, open your Claude configuration file located here:
   `%APPDATA%\Claude\claude_desktop_config.json`

   Add the following configuration to run the server locally:
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

## EC2 Deployment (Ubuntu)

If you are deploying this MCP server to an Ubuntu EC2 instance (e.g. Ubuntu 22.04 or 24.04), follow these steps to securely configure the server using the FastAPI implementation (`src/server2.py`).

### 1. Update and Install Dependencies
SSH into your EC2 instance and run the following commands to install Python 3 and Git:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install git python3 python3-pip python3-venv -y
```

### 2. Clone the Repository
```bash
git clone https://github.com/MiKecantdothis/MCPforGBL.git
cd MCPforGBL
```

### 3. Setup Virtual Environment & Install Packages
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Create your Environment Variables
Since your secrets are safely `.gitignore`'d, you must create the `.env` file manually on the EC2 instance:
```bash
nano .env
```
*(Paste your database credentials inside, save with `Ctrl+O`, `Enter`, and exit with `Ctrl+X`.)*

### 5. Run the Server (HTTP/SSE)
To start the FastAPI HTTP server and keep it running in the background even after you close your SSH connection, use `nohup`:
```bash
nohup python3 -m src.server2 > server.log 2>&1 &
```
> **Note:** Your FastAPI server will now be accessible via your EC2 instance's IP on port 8000. **Important**: Make sure you edit your instance's **Security Group** in the AWS console to allow Inbound TCP traffic on **Port 8000**.

### 6. Generate an API Key (for HTTP/SSE)
To secure your remote HTTP/SSE server, it requires valid API keys (`src/server2.py`).
Run the auth module to generate a strong key and save it to `api_keys.json`:
```bash
python3 -m src.auth generate "ClientName"
```

### 7. Connect Claude Desktop to EC2
If you exposed Port 8000 publicly over HTTP/SSE, update `%APPDATA%\Claude\claude_desktop_config.json` on Windows to pass your generated key in the headers:
```json
{
  "mcpServers": {
    "brand-db-remote": {
      "command": "C:\\Program Files\\nodejs\\npx.cmd",
      "args": [
        "-y", 
        "mcp-remote", 
        "http://YOUR-EC2-PUBLIC-IP:8000/sse", 
        "--allow-http",
        "--header", 
        "Authorization: Bearer YOUR_GENERATED_KEY"
      ]
    }
  }
}
```

If you prefer not to expose Port 8000 publicly and want Claude Desktop to communicate securely via SSH to your newly launched EC2 instance, use the standard `stdio` configuration. 

Open `%APPDATA%\Claude\claude_desktop_config.json` on your Windows machine and add:
```json
{
  "mcpServers": {
    "brand-db-remote": {
      "command": "ssh",
      "args": [
        "-i", "C:/path/to/your/ec2-key.pem",
        "ubuntu@YOUR-EC2-PUBLIC-IP",
        "cd /home/ubuntu/MCPforGBL && source .venv/bin/activate && python3 -m src.server"
      ]
    }
  }
}
```
*(This setup seamlessly securely tunnels Claude's requests via SSH directly into your EC2's standard input/output server!)*
