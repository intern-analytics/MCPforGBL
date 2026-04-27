from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os
from datetime import datetime, timezone
from src.auth import generate_api_key, revoke_api_key, load_keys, revalidate_api_key, update_api_key_password

app = FastAPI(title="Brand MCP Server - Internal Admin API")

# Ensure static directory exists
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

# Mount static files for the UI
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

class GenerateRequest(BaseModel):
    db_user: str
    db_pass: str

class UpdatePasswordRequest(BaseModel):
    new_pass: str

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard():
    """Serves the Admin UI dashboard."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            return f.read()
    return "<h1>Admin UI Not Found</h1><p>Please ensure src/static/index.html exists.</p>"

@app.post("/keys/generate")
async def api_generate_key(payload: GenerateRequest):
    try:
        new_key = generate_api_key(
            db_user=payload.db_user, 
            db_pass=payload.db_pass
        )
        return {"success": True, "api_key": new_key, "db_user": payload.db_user}
    except ValueError as e:
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

            safe_list.append({
                "db_user": data.get("db_user"),
                "key_prefix": key[:8] + "..." if key else None,
                "expires_at": expires_at_str,
                "status": status_str
            })
    return {"managed_keys": safe_list}

@app.delete("/keys/{db_user}")
async def api_revoke_key(db_user: str):
    success = revoke_api_key(db_user)
    if success:
        return {"success": True, "message": f"Successfully revoked access for db_user '{db_user}'"}
    else:
        raise HTTPException(status_code=404, detail="No key found for that db_user")

@app.put("/keys/{db_user}/revalidate")
async def api_revalidate_key(db_user: str):
    data = revalidate_api_key(db_user)
    if data:
        return {
            "success": True, 
            "message": f"Successfully revalidated access for db_user '{db_user}'", 
            "new_expiry": data.get("expires_at")
        }
    else:
        raise HTTPException(status_code=404, detail="No key found for that db_user")

@app.put("/keys/{db_user}/password")
async def api_update_password(db_user: str, payload: UpdatePasswordRequest):
    data = update_api_key_password(db_user, payload.new_pass)
    if data:
        return {
            "success": True,
            "message": f"Successfully updated password for db_user '{db_user}'"
        }
    else:
        raise HTTPException(status_code=404, detail="No key found for that db_user")

if __name__ == "__main__":
    print("\nAdmin Dashboard available at: http://127.0.0.1:8001/admin")
    print("Server running strictly on loopback for security.\n")
    uvicorn.run("src.admin_api:app", host="127.0.0.1", port=8001, reload=True)
