import os
import json
import sys
from typing import Any, List, Dict
from pathlib import Path
import mcp.types as types
from mcp.server import Server
from src.db import run_query
from src.auth import authorized_brands_var

BRANDS_DIR = Path(__file__).parent / "brands"

def load_brand_configs() -> Dict[str, Dict]:
    """Loads all brand JSON configurations from the brands directory."""
    brands = {}
    if not BRANDS_DIR.exists():
        os.makedirs(BRANDS_DIR, exist_ok=True)
        return brands
        
    for file in BRANDS_DIR.glob("*.json"):
        try:
            with open(file, "r") as f:
                config = json.load(f)
                brand_id = config.get("brand_id")
                if brand_id:
                    brands[brand_id] = config
        except Exception as e:
            print(f"Error loading brand config {file}: {e}", file=sys.stderr)
    return brands

def register_tools(server: Server):
    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        tools = []
        authorized_brands = authorized_brands_var.get() or {}
        
        # Check if user has powerbi_readonlyuser anywhere
        has_powerbi = any(b.get("db_user") == "powerbi_readonlyuser" for b in authorized_brands.values())

        if has_powerbi:
            tools.append(types.Tool(
                name="list_tables",
                description="Returns a list of all accessible tables across all schemas",
                inputSchema={"type": "object", "properties": {}}
            ))

        # Load dynamic brand tools
        brands = load_brand_configs()
        has_brand_tools = False

        for brand_id, config in brands.items():
            # Security: Only list the tool if the user is authorized for this brand
            is_authorized = brand_id in authorized_brands or "unbranded" in authorized_brands
            
            # Superuser override
            if any(b.get("db_user") in ["postgres", "powerbi_readonlyuser"] for b in authorized_brands.values()):
                is_authorized = True
                
            if not is_authorized:
                continue

            has_brand_tools = True

            # Build a rich description using schema and instructions
            final_tool_name = f"{config.get('tool_name', brand_id)}"
            
            tool_description = (
                "### PROFESSIONAL REPORTING STANDARDS\n"
                "1. BUSINESS-ONLY OUTPUT: Your response must focus strictly on business growth and results. Avoid all technical references.\n"
                "2. NO DATA NARRATION: Do not describe your internal data-finding process (e.g., skip 'Let me check...' or 'Scanning tables...'). Perform queries silently.\n"
                "3. NO TECHNICAL IDENTIFIERS: Do not mention internal table names, column names, or schema paths in your conversation.\n"
                "4. NATURAL BUSINESS TONE: Provide data-driven answers as if presenting to an executive.\n\n"
                f"BRAND: {config.get('display_name', brand_id)}\n\n"
                "### ANALYST LOGIC PROTOCOLS:\n"
                f"{config.get('schema_details', '')}\n\n"
                f"{config.get('specific_instructions', '')}"
            )

            tools.append(types.Tool(
                name=final_tool_name,
                description=tool_description,
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": f"The SELECT query for {config.get('display_name')}"
                        }
                    },
                    "required": ["sql"]
                }
            ))
        
        if has_powerbi:
            # Keep the legacy execute_query for backward compatibility or admin use
            tools.append(types.Tool(
                name="execute_query",
                description="Executes a raw read-only SQL query against the database.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string", "description": "The SELECT query to execute"}
                    },
                    "required": ["sql"]
                }
            ))
        
        return tools

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        arguments = arguments or {}
        authorized_brands = authorized_brands_var.get() or {}

        if name == "list_tables":
            # Find powerbi credentials
            powerbi_creds = next((b for b in authorized_brands.values() if b.get("db_user") == "powerbi_readonlyuser"), None)
            if not powerbi_creds:
                raise ValueError("Unauthorized access to list_tables")
            try:
                results = await run_query(
                    "SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema NOT IN ('information_schema', 'pg_catalog')",
                    db_user=powerbi_creds["db_user"],
                    db_pass=powerbi_creds["db_pass"]
                )
                return [types.TextContent(type="text", text=json.dumps(results, indent=2))]
            except Exception as e:
                return [types.TextContent(type="text", text=f"Error listing tables: {e}")]

        # Check for brand-specific tool calls
        brands = load_brand_configs()
        for brand_id, config in brands.items():
            if name == config.get("tool_name"):
                sql = arguments.get("sql")
                if not sql:
                    raise ValueError("sql argument is required")
                
                # Retrieve the specific credentials for this brand execution
                is_authorized = brand_id in authorized_brands or "unbranded" in authorized_brands
                
                # Check for superuser fallback
                super_creds = next((b for b in authorized_brands.values() if b.get("db_user") in ["postgres", "powerbi_readonlyuser"]), None)
                
                creds = None
                if brand_id in authorized_brands:
                    creds = authorized_brands[brand_id]
                elif "unbranded" in authorized_brands:
                    creds = authorized_brands["unbranded"]
                elif super_creds:
                    creds = super_creds
                    
                if not is_authorized and not super_creds:
                    raise ValueError(f"Unauthorized access to tool {name}")
                
                if not creds:
                    raise ValueError(f"No database credentials found for tool {name}")

                try:
                    results = await run_query(sql, db_user=creds["db_user"], db_pass=creds["db_pass"])
                    return [types.TextContent(type="text", text=json.dumps(results, indent=2, default=str))]
                except Exception as e:
                    return [types.TextContent(type="text", text=f"Error executing {config['display_name']} query: {e}")]

        if name == "execute_query":
            sql = arguments.get("sql")
            if not sql:
                raise ValueError("sql argument is required")
                
            powerbi_creds = next((b for b in authorized_brands.values() if b.get("db_user") == "powerbi_readonlyuser"), None)
            if not powerbi_creds:
                 raise ValueError("Unauthorized access to execute_query")
                 
            try:
                results = await run_query(sql, db_user=powerbi_creds["db_user"], db_pass=powerbi_creds["db_pass"])
                return [types.TextContent(type="text", text=json.dumps(results, indent=2, default=str))]
            except Exception as e:
                return [types.TextContent(type="text", text=f"Error executing query: {e}")]

        raise ValueError(f"Unknown tool: {name}")
