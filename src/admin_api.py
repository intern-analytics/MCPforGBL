from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from src.auth import generate_api_key, revoke_api_key, load_keys

app = FastAPI(title="Brand MCP Server - Internal Admin API")

class GenerateRequest(BaseModel):
    db_user: str
    db_pass: str

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
    
    for key, data in keys.items():
        if isinstance(data, dict):
            safe_list.append({
                "db_user": data.get("db_user"),
                "key_prefix": key[:8] + "..." if key else None
            })
    return {"managed_keys": safe_list}

@app.delete("/keys/{db_user}")
async def api_revoke_key(db_user: str):
    success = revoke_api_key(db_user)
    if success:
        return {"success": True, "message": f"Successfully revoked access for db_user '{db_user}'"}
    else:
        raise HTTPException(status_code=404, detail="No key found for that db_user")

if __name__ == "__main__":
    print("Starting Admin API strictly on loopback (127.0.0.1:8001)")
    uvicorn.run("src.admin_api:app", host="127.0.0.1", port=8001, reload=True)
