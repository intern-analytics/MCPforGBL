---
name: chumbak-db-ops
description: >
  Use this skill whenever a user asks about Chumbak sales, orders, inventory,
  purchase orders, products, revenue, or any analytics derived from Chumbak
  data. Triggers on queries like "show me Chumbak sales", "what's the inventory
  for SKU X", "how many orders did we get last month", "top selling products",
  "fill rate", "channel revenue", or any request that would require querying the
  Chumbak Postgres database. Always use this skill before writing any SQL
  involving Chumbak tables — it contains mandatory schema rules, join keys, and
  query standards that must be followed precisely.
---

# Chumbak Database Operations

This skill defines how the MCP server interacts with the **Chumbak Postgres database**.

> **Schema rule**: All tables must be prefixed with `"DataWarehouse"` — e.g., `"DataWarehouse".chumbak_sale_orders`. Never reference a table without this prefix.

---

## Available Tools

### 1. `list_tables`
- **Description**: Returns a list of all accessible tables in the current database schema.
- **Input**: None
- **Output**: Array of table names.

### 2. `execute_query`
- **Description**: Executes a read-only (SELECT) SQL query.
- **Input**: `{"sql": "string"}`
- **Output**: Array of row objects from the database.

---

## Tables in Scope

### 1. `"DataWarehouse".chumbak_in_unicommerce_saleorders`
- **Join key**: `"Item SKU Code"` (`character varying`)
- **Date column**: `"Order Date as dd/mm/yyyy hh:MM:ss"` (`timestamp with time zone`) ← always wrap in `DATE()`
- **Use for**: Orders, revenue, channel analysis, fulfilment status

### 2. `"DataWarehouse".chumbak_in_unicommerce_inventorysnapshot`
- **Join key**: `"Item SkuCode"` (`character varying`)
- **Date column**: `"Inventory Snapshot Date"` (`date`)
- **Use for**: Inventory levels, blocked stock, open sales, pending assessment

### 3. `"DataWarehouse".chumbak_in_unicommerce_purchaseorders`
- **Join key**: `"Item SkuCode"` (`character varying`)
- **Date column**: `"updatedAt"` (`timestamp with time zone`) ← always wrap in `DATE()`
- **Use for**: Purchase orders, received vs ordered quantities, PO status

### 4. `"DataWarehouse".chumbak_in_unicommerce_itemmaster`
- **Join key**: `"Product Code"` (`character varying`) — primary
- **Fallback join**: `"EAN"` (`character varying`) — use only when SKU join is not possible
- **Use for**: Product metadata, descriptions, dimensions, pricing

---

## Join Rules

Always use SKU-based joins. Use `"EAN"` only as a fallback when joining to `chumbak_itemmaster`.

```sql
-- Sales ↔ Inventory
ON so."Item SKU Code" = inv."Item SkuCode"

-- Sales ↔ Purchase Orders
ON so."Item SKU Code" = po."Item SkuCode"

-- Sales ↔ Item Master (SKU — preferred)
ON so."Item SKU Code" = im."Product Code"

-- Sales ↔ Item Master (EAN — fallback only)
ON so."Item Type EAN" = im."EAN"
```

---

## Date Handling

- All date filter values must be in `YYYY-MM-DD` format.
- `timestamp with time zone` columns must be wrapped in `DATE()` before filtering.
- `date` type columns (e.g. `"Inventory Snapshot Date"`) can be compared directly without wrapping.

```sql
-- Timestamp column (chumbak_sale_orders) — wrap in DATE()
WHERE DATE(so."Order Date as dd/mm/yyyy hh:MM:ss") BETWEEN '2025-01-01' AND '2025-01-31'

-- Date column (chumbak_inventory_snapshot) — compare directly
WHERE inv."Inventory Snapshot Date" BETWEEN '2025-01-01' AND '2025-01-31'

-- Timestamp column (chumbak_purchase_orders) — wrap in DATE()
WHERE DATE(po."updatedAt") BETWEEN '2025-01-01' AND '2025-01-31'
```

---

## Brand Query Rules

1. **Read-Only Restrictions**: Reject any query containing `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, or `TRUNCATE` — do not execute, explain why.
2. **Limit Results**: Always apply `LIMIT 100` unless the user explicitly requests otherwise.
3. **Data Privacy**: Do not query or return PII (names, addresses, phone numbers, email, GSTIN) unless explicitly required and authorised.
4. **`"DataWarehouse"` schema only**: Never reference tables outside this schema.
5. **Always include a date filter**: Queries without a date range must be rejected.
6. **Never use `SELECT *`**: List only the columns needed for the task.
7. **Never guess column names**: Use only the columns listed in this skill.

---

## Common Metric Patterns

```sql
-- Revenue
SUM(so."Selling Price")

-- Distinct order count
COUNT(DISTINCT so."Sale Order Code")

-- Available inventory (net of blocked stock)
inv."Inventory" - inv."Inventory Blocked"

-- PO fill rate
po."Recieved Quantity"::float / NULLIF(po."Order Quantity", 0)
```

> Note: `"Recieved Quantity"` is the actual column name in the database (intentional typo — do not correct it).

---

## Reference Query

```sql
SELECT
    so."Channel Name",
    COUNT(DISTINCT so."Sale Order Code") AS orders,
    SUM(so."Selling Price")              AS revenue
FROM "DataWarehouse".chumbak_sale_orders so
WHERE DATE(so."Order Date as dd/mm/yyyy hh:MM:ss")
      BETWEEN '2025-01-01' AND '2025-01-31'
GROUP BY 1
ORDER BY revenue DESC
LIMIT 100;
```