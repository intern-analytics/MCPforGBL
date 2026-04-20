import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextvars import ContextVar

# Context variables for per-request database credentials
db_user_var: ContextVar[str | None] = ContextVar("db_user_var", default=None)
db_pass_var: ContextVar[str | None] = ContextVar("db_pass_var", default=None)


API_KEYS_FILE = Path(__file__).parent.parent / "api_keys.json"
security = HTTPBearer(auto_error=False)

def load_keys() -> dict:
    if not API_KEYS_FILE.exists():
        return {}
    try:
        with open(API_KEYS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_keys(keys: dict):
    with open(API_KEYS_FILE, "w") as f:
        json.dump(keys, f, indent=2)

def generate_api_key(db_user: str, db_pass: str) -> str:
    keys = load_keys()
    
    # Enforce uniqueness mapping: one API key per exact DB user mapped
    for key, data in keys.items():
        if isinstance(data, dict) and data.get("db_user") == db_user:
            raise ValueError(f"db_user '{db_user}' is already registered to an existing key.")
    
    # Generate a random 32-byte hex string
    new_key = "gbl-" + secrets.token_hex(32)
    
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=90)
    
    keys[new_key] = {
        "db_user": db_user,
        "db_pass": db_pass,
        "created_at": now.isoformat(),
        "expires_at": expires.isoformat()
    }
    save_keys(keys)
    return new_key

def revoke_api_key(db_user: str) -> bool:
    keys = load_keys()
    
    for key, data in list(keys.items()):
        # Handle backwards compatibility with flat string mappings
        target = data.get("db_user") if isinstance(data, dict) else data
        if target == db_user:
            del keys[key]
            save_keys(keys)
            return True
    return False

def revalidate_api_key(db_user: str) -> dict | None:
    keys = load_keys()
    
    for key, data in keys.items():
        if isinstance(data, dict) and data.get("db_user") == db_user:
            now = datetime.now(timezone.utc)
            expires = now + timedelta(days=90)
            data["expires_at"] = expires.isoformat()
            save_keys(keys)
            return data
    return None

async def verify_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = None
    if credentials:
        token = credentials.credentials
    
    if not token:
        token = request.query_params.get("token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    keys = load_keys()
    data = keys.get(token)
    
    if not data or not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    now = datetime.now(timezone.utc)
    expires_at_str = data.get("expires_at")
    
    if not expires_at_str:
        # Migration: set expiry to 90 days from now
        expires = now + timedelta(days=90)
        data["created_at"] = now.isoformat()
        data["expires_at"] = expires.isoformat()
        save_keys(keys)
    else:
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if now > expires_at:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API Key Expired. Please revalidate.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except ValueError:
            pass # Ignore invalid formats for now
    
    # Map the securely fetched credentials out, securely tying them down
    request.state.db_user = data.get("db_user")
    request.state.db_pass = data.get("db_pass")
    
    return data
