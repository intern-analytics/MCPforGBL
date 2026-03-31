---
name: Database Operations Skill
description: Documents tools, inputs/outputs, and brand query rules for the MCP server.
---

# Database Operations

This skill defines how the MCP server interacts with the brand Postgres databases.

## Available Tools

### 1. `list_tables`
- **Description**: Returns a list of all accessible tables in the current database schema.
- **Input**: None
- **Output**: Array of table names.

### 2. `execute_query`
- **Description**: Executes a read-only (SELECT) SQL query.
- **Input**: `{"sql": "string"}`
- **Output**: Array of row objects from the database.


## Brand Query Rules
1. **Read-Only Restrictions**: The MCP server must reject any queries containing `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, or `TRUNCATE`.
2. **Limit Results**: Queries should generally be limited to a reasonable number of rows (e.g., `LIMIT 100`) to avoid overwhelming the context window.
3. **Data Privacy**: Do not query or return PII (Personally Identifiable Information) unless explicitly required and authorized.

