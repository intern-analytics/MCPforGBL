import asyncio
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from src.auth import verify_api_key
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
async def handle_sse(request: Request, token: str = Depends(verify_api_key)):
    """The main Server-Sent Events endpoint for MCP clients."""
    # SseServerTransport.connect_sse requires the ASGI scope, receive, and send callables
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as (read_stream, write_stream):
        await app.run(
            read_stream, write_stream, app.create_initialization_options()
        )

@fastapi_app.post("/messages")
async def handle_messages(request: Request, token: str = Depends(verify_api_key)):
    """Endpoint for MCP clients to POST incoming messages."""
    await sse.handle_post_message(request.scope, request.receive, request._send)

if __name__ == "__main__":
    print("Starting Brand MCP SSE Server on http://0.0.0.0:8000")
    uvicorn.run("src.server2:fastapi_app", host="0.0.0.0", port=8000, reload=True)
