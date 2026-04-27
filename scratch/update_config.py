import json
import io

with io.open(r'c:\Users\Mike\Desktop\Chumbak MCP\brand-mcp-server\src\brands\chumbak_config.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

specific = data['specific_instructions']
schema = data['schema_details']

# Update SCHEMA PREFIX RULE
specific = specific.replace(
    '- The Myntra SJIT crawler table lives in the public schema.',
    '- The Myntra SJIT crawler tables (sales and inventory) live in the public schema.'
)

# Replace Myntra sales definition
old_sales = "(7) public.myntra_crawler_sjit_chumbak_sales — Myntra SJIT self-ship orders, crawled directly from Myntra seller portal. Independent of Unicommerce.\n    - Schema: public (NOT \"DataWarehouse\").\n    - Join key: seller_sku_code"
new_sales = "(7) public.myntra_crawler_sjit_chumbak_sales — Myntra SJIT self-ship orders, crawled directly from Myntra seller portal. Independent of Unicommerce.\n    - Schema: public (NOT \"DataWarehouse\").\n    - MANDATORY filter: brand = 'blinkit' (logically represents Chumbak).\n    - Join key: seller_sku_code"

specific = specific.replace(old_sales, new_sales)

# Add Myntra inventory definition
inv_add = """
(7.1) public.myntra_crawler_sjit_chumbak_inventories — Myntra SJIT self-ship inventory, crawled directly from Myntra seller portal.
    - Schema: public (NOT "DataWarehouse").
    - MANDATORY filter: brand = 'blinkit' (logically represents Chumbak).
    - Join key: seller_sku_code (character varying)."""

insert_pos = specific.find('(8) "DataWarehouse".chumbak_ebo_sales')
if insert_pos != -1:
    specific = specific[:insert_pos] + inv_add.strip() + '\n\n' + specific[insert_pos:]
else:
    print("Could not find (8)")

# Update schema_details
old_schema = "[[[ PUBLIC SCHEMA — MYNTRA ]]]\n- myntra_crawler_sjit_chumbak_sales: Myntra self-ship portal revenue. created_on is varchar ISO."
new_schema = "[[[ PUBLIC SCHEMA — MYNTRA ]]]\n- myntra_crawler_sjit_chumbak_sales: Myntra self-ship portal revenue. created_on is varchar ISO. MANDATORY filter: brand = 'blinkit' (treat as Chumbak).\n- myntra_crawler_sjit_chumbak_inventories: Myntra self-ship portal inventory. MANDATORY filter: brand = 'blinkit' (treat as Chumbak)."

schema = schema.replace(old_schema, new_schema)

data['specific_instructions'] = specific
data['schema_details'] = schema

with io.open(r'c:\Users\Mike\Desktop\Chumbak MCP\brand-mcp-server\src\brands\chumbak_config.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
