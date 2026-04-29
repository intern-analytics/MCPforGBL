import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from src.auth import verify_api_key, db_user_var, db_pass_var
from src.db import close_all_pools
from mcp.server import Server
from mcp.server.sse import SseServerTransport
import uvicorn

from src.admin_api import app as admin_app
from src.tools import register_tools

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Dynamic connection pooling uses lazy loading, so we only handle the shutdown."""
    yield
    await close_all_pools()

# Create the MCP server instance
app = Server("brand-mcp-server")

# Register your existing tools with the server
register_tools(app)

# Initialize the SSE transport
sse = SseServerTransport("/messages", keep_alive_interval=15)

# Build the FastAPI application
fastapi_app = FastAPI(title="Brand MCP HTTP/SSE Server", lifespan=lifespan)

# Add CORS middleware 
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://claude.ai", "http://localhost:5173", "http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Active Session Bridge (To support Claude Web UI parameter dropping)
active_sessions = {}
sse_lock = asyncio.Lock()

@fastapi_app.get("/")
async def root():
    """A simple root endpoint to verify the server is running."""
    return JSONResponse({"status": "brand-mcp-server running directly on FastAPI HTTP/SSE"})

@fastapi_app.get("/health")
async def health():
    """Reports the live status of the server and the database connection pools."""
    from src.db import _pools
    total = sum(p.get_size() for p in _pools.values())
    idle = sum(p.get_idle_size() for p in _pools.values())
    return JSONResponse({
        "status": "healthy",
        "pools_active": len(_pools),
        "total_connections": total,
        "total_idle": idle
    })

@fastapi_app.get("/sse")
async def handle_sse(request: Request, token_data: dict = Depends(verify_api_key)):
    """The main Server-Sent Events endpoint for MCP clients."""
    # Set context variables for the current request
    db_user_var.set(token_data.get("db_user"))
    db_pass_var.set(token_data.get("db_pass"))
    # We securely bind the verified API token context to the actual internal session UUID stream
    async with sse_lock:
        before_keys = set(sse._read_stream_writers.keys())
        ctx = sse.connect_sse(request.scope, request.receive, request._send)
        streams = await ctx.__aenter__()
        
        after_keys = set(sse._read_stream_writers.keys())
        diff = list(after_keys - before_keys)
        if diff:
            session_id = diff[0]
            active_sessions[session_id.hex] = token_data
            
    try:
        await app.run(streams[0], streams[1], app.create_initialization_options())
    finally:
        await ctx.__aexit__(None, None, None)
        if diff:
            active_sessions.pop(session_id.hex, None)

async def custom_messages_app(scope, receive, send):
    """An ASGI wrapper enabling dynamic Auth extraction for Claude Web UI."""
    request = Request(scope)
    session_id = request.query_params.get("session_id")
    
    if not session_id or session_id not in active_sessions:
        response = JSONResponse({"detail": "Unauthorized session"}, status_code=401)
        return await response(scope, receive, send)
        
    token_data = active_sessions[session_id]
    scope.setdefault("state", {})
    scope["state"]["db_user"] = token_data.get("db_user")
    scope["state"]["db_pass"] = token_data.get("db_pass")
    
    # Set context variables for the POST message request
    db_user_var.set(token_data.get("db_user"))
    db_pass_var.set(token_data.get("db_pass"))
    
    await sse.handle_post_message(scope, receive, send)

# Mount it natively entirely bypassing FastAPI runtime execution wrappers!
fastapi_app.mount("/messages", custom_messages_app)

# Mount the internal Admin API Sub-application
fastapi_app.mount("/admin-api", admin_app)

if __name__ == "__main__":
    print("Starting Brand MCP SSE Server on http://0.0.0.0:8000")
    uvicorn.run("src.server2:fastapi_app", host="0.0.0.0", port=8000, reload=True)
