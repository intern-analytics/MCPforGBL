import os
from typing import Any, List
import json
import mcp.types as types
from mcp.server import Server
from src.db import run_query
from src.auth import db_user_var, db_pass_var

def register_tools(server: Server):
    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="list_tables",
                description="Returns a list of all accessible tables across all schemas",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            types.Tool(
                name="execute_query",
                description="Executes a read-only SQL query against the database",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": "The SELECT query to execute"
                        }
                    },
                    "required": ["sql"]
                }
            )
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        arguments = arguments or {}

        # Retrieve credentials from the verified context
        db_user = db_user_var.get()
        db_pass = db_pass_var.get()

        if name == "list_tables":
            try:
                results = await run_query(
                    "SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema NOT IN ('information_schema', 'pg_catalog')",
                    db_user=db_user,
                    db_pass=db_pass
                )
                return [types.TextContent(type="text", text=json.dumps(results, indent=2))]
            except Exception as e:
                return [types.TextContent(type="text", text=f"Error listing tables: {e}")]

        if name == "execute_query":
            sql = arguments.get("sql")
            if not sql:
                raise ValueError("sql argument is required")
            try:
                results = await run_query(sql, db_user=db_user, db_pass=db_pass)
                return [types.TextContent(type="text", text=json.dumps(results, indent=2, default=str))]
            except Exception as e:
                return [types.TextContent(type="text", text=f"Error executing query: {e}")]

        raise ValueError(f"Unknown tool: {name}")
