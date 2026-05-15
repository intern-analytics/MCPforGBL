from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
import json
from datetime import datetime, timezone
from src.auth import generate_api_key, revoke_api_key, load_keys, revalidate_api_key, update_db_user_password, update_db_user_username, revoke_all_by_email, revoke_brand_by_email

app = FastAPI(title="Brand MCP Server - Internal Admin API")

# Ensure static directory exists
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

# Mount static files for the UI
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

class GenerateRequest(BaseModel):
    end_user: str
    brand_name: str | None = None
    brand_names: list[str] = []

class UpdatePasswordRequest(BaseModel):
    new_pass: str

class UpdateUsernameRequest(BaseModel):
    new_db_user: str

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard():
    """Serves the Admin UI dashboard."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Admin UI Not Found</h1><p>Please ensure src/static/index.html exists.</p>"


@app.get("/brands")
async def api_list_brands():
    # Brand IDs in this list are hidden from the public portal and admin UI dropdown
    HIDDEN_BRANDS = {"super_user", "rainbow_brands"}
    brands = []
    brands_dir = os.path.join(os.path.dirname(__file__), "brands")
    if os.path.exists(brands_dir):
        for filename in os.listdir(brands_dir):
            if filename.endswith("_config.json"):
                filepath = os.path.join(brands_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        brand_id = data.get("brand_id")
                        tool_name = data.get("tool_name", brand_id)
                        if brand_id and brand_id not in HIDDEN_BRANDS:
                            brands.append({"brand_id": brand_id, "tool_name": tool_name})
                except Exception:
                    pass
    # Sort alphabetically by tool_name
    brands.sort(key=lambda x: x["tool_name"])
    return {"brands": brands}

@app.post("/keys/generate")
async def api_generate_key(payload: GenerateRequest):
    brands_to_add = [b.lower().strip() for b in payload.brand_names if b.strip()]
    if payload.brand_name and payload.brand_name.strip():
        brands_to_add.append(payload.brand_name.lower().strip())
        
    if not brands_to_add:
        raise HTTPException(status_code=400, detail="Must provide at least one brand.")
        
    brands_to_add = list(set(brands_to_add))
    
    valid_brands = []
    brands_dir = os.path.join(os.path.dirname(__file__), "brands")
    if os.path.exists(brands_dir):
        for filename in os.listdir(brands_dir):
            if filename.endswith("_config.json"):
                filepath = os.path.join(brands_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if "brand_id" in data:
                            valid_brands.append(data["brand_id"].lower())
                except Exception:
                    pass
    valid_brands.append("super_user")

    for brand in brands_to_add:
        if brand not in valid_brands:
            raise HTTPException(status_code=400, detail=f"Invalid brand name: {brand}. Available options: {', '.join(valid_brands)}")

    new_key = None
    already_had_access = []
    brands_added = []
    try:
        for brand in brands_to_add:
            if brand == "super_user":
                db_user = os.getenv("SUPER_DB_USER", "postgres")
                db_pass = os.getenv("SUPER_DB_PASS", "secret")
            else:
                db_user = os.getenv(f"{brand.upper()}_DB_USER", f"{brand}_user")
                db_pass = os.getenv(f"{brand.upper()}_DB_PASS", "secret")

            try:
                current_key = generate_api_key(
                    end_user=payload.end_user,
                    brand_id=brand,
                    db_user=db_user, 
                    db_pass=db_pass
                )
                if not new_key:
                    new_key = current_key
                brands_added.append(brand)
            except ValueError as e:
                # Catch the 'already registered' error and continue
                if "already registered" in str(e) or "already has access" in str(e):
                    already_had_access.append(brand)
                else:
                    raise e
                    
        # If no key was captured because all brands already existed, find their key
        if not new_key:
            keys = load_keys()
            for k, data in keys.items():
                if isinstance(data, dict) and data.get("end_user") == payload.end_user:
                    new_key = k
                    break
                    
        if not new_key:
            raise HTTPException(status_code=400, detail="Failed to retrieve or generate API key.")

        # Load keys to get the expiration date
        keys = load_keys()
        key_data = keys.get(new_key, {})
        valid_till = key_data.get("expires_at", "")
        
        # Try to find a nice display name for the brands
        display_names = []
        if os.path.exists(brands_dir):
            for brand in brands_to_add:
                d_name = brand.capitalize()
                filepath = os.path.join(brands_dir, f"{brand}_config.json")
                if os.path.exists(filepath):
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            d_name = data.get("display_name", d_name)
                    except Exception:
                        pass
                display_names.append(d_name)
        
        combined_display_name = ", ".join(display_names)

        # Send the generated API key via email
        from src.email_service import send_api_key_email
        send_api_key_email(payload.end_user, new_key, valid_till, combined_display_name)
        
        message_parts = []
        if brands_added:
            message_parts.append(f"Successfully added access to: {', '.join(brands_added)}")
        if already_had_access:
            message_parts.append(f"User already had access to: {', '.join(already_had_access)}")
            
        return {
            "success": True, 
            "api_key": new_key, 
            "end_user": payload.end_user, 
            "brand_names": brands_to_add,
            "message": ". ".join(message_parts)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/keys")
async def api_list_keys():
    keys = load_keys()
    safe_list = []
    now = datetime.now(timezone.utc)
    
    for key, data in keys.items():
        if isinstance(data, dict):
            status_str = "Active"
            expires_at_str = data.get("expires_at")
            if expires_at_str:
                try:
                    expires_at = datetime.fromisoformat(expires_at_str)
                    if now > expires_at:
                        status_str = "Expired"
                except ValueError:
                    status_str = "Unknown"
            else:
                status_str = "Active (Pending Migration)"

            brands_list = []
            if "brands" in data:
                brands_list = list(data["brands"].keys())
            elif data.get("brand_id"):
                brands_list = [data["brand_id"]]

            safe_list.append({
                "end_user": data.get("end_user") or data.get("db_user"),
                "db_user": data.get("db_user"),
                "key_prefix": key[:8] + "..." if key else None,
                "expires_at": expires_at_str,
                "status": status_str,
                "brands": brands_list
            })
    return {"managed_keys": safe_list}

@app.delete("/keys/by-email")
async def api_revoke_all_by_email(email: str):
    success = revoke_all_by_email(email)
    if success:
        return {"success": True, "message": f"Revoked all access for '{email}'"}
    raise HTTPException(status_code=404, detail="No key found for that email")

@app.delete("/keys/brand")
async def api_revoke_brand(email: str, brand_id: str):
    success = revoke_brand_by_email(email, brand_id)
    if success:
        return {"success": True, "message": f"Revoked '{brand_id}' access for '{email}'"}
    raise HTTPException(status_code=404, detail="No key or brand found for that email")

@app.delete("/keys")
async def api_revoke_key(end_user: str, db_user: str):
    success = revoke_api_key(end_user, db_user)
    if success:
        return {"success": True, "message": f"Successfully revoked access for end_user '{end_user}' on '{db_user}'"}
    else:
        raise HTTPException(status_code=404, detail="No key found for that end_user and db_user")

@app.put("/keys/revalidate")
async def api_revalidate_key(end_user: str, db_user: str):
    data = revalidate_api_key(end_user, db_user)
    if data:
        return {
            "success": True, 
            "message": f"Successfully revalidated access for end_user '{end_user}' on '{db_user}'", 
            "new_expiry": data.get("expires_at")
        }
    else:
        raise HTTPException(status_code=404, detail="No key found for that end_user and db_user")

@app.put("/keys/{db_user}/password")
async def api_update_password(db_user: str, payload: UpdatePasswordRequest):
    count = update_db_user_password(db_user, payload.new_pass)
    if count > 0:
        return {
            "success": True,
            "message": f"Successfully updated password for db_user '{db_user}' (affected {count} keys)"
        }
    else:
        raise HTTPException(status_code=404, detail="No keys found for that db_user")

@app.patch("/keys/{db_user}/username")
async def api_update_username(db_user: str, payload: UpdateUsernameRequest):
    count = update_db_user_username(db_user, payload.new_db_user)
    if count > 0:
        return {
            "success": True,
            "message": f"Successfully renamed db_user '{db_user}' to '{payload.new_db_user}' (affected {count} keys)"
        }
    else:
        raise HTTPException(status_code=404, detail=f"No keys found for db_user '{db_user}'")

if __name__ == "__main__":
    print("\nAdmin Dashboard available at: http://127.0.0.1:8003/admin")
    print("Server running strictly on loopback for security.\n")
    uvicorn.run("src.admin_api:app", host="127.0.0.1", port=8003, reload=True)
