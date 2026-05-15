import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextvars import ContextVar

# Context variables for per-request database credentials
authorized_brands_var: ContextVar[dict | None] = ContextVar("authorized_brands_var", default=None)

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

def _migrate_key_to_brands(data: dict) -> dict:
    """Helper to migrate old flat token data to the new nested brands structure."""
    if "brands" not in data:
        data["brands"] = {}
        if data.get("brand_id"):
            data["brands"][data.get("brand_id")] = {
                "db_user": data.get("db_user"),
                "db_pass": data.get("db_pass")
            }
        elif data.get("db_user"): # superuser or unbranded
            data["brands"]["unbranded"] = {
                "db_user": data.get("db_user"),
                "db_pass": data.get("db_pass")
            }
    return data

def generate_api_key(end_user: str, brand_id: str, db_user: str, db_pass: str) -> str:
    keys = load_keys()
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=90)
    
    # Check if end_user already has an API key
    for key, data in keys.items():
        if isinstance(data, dict):
            existing_user = data.get("end_user") or data.get("db_user")
            if existing_user == end_user:
                # User exists! Append to their brands.
                data = _migrate_key_to_brands(data)
                
                # Check if this exact db_user is already mapped for this brand
                if brand_id in data["brands"] and data["brands"][brand_id].get("db_user") == db_user:
                    raise ValueError(f"end_user '{end_user}' is already registered for this tool.")
                
                data["brands"][brand_id] = {
                    "db_user": db_user,
                    "db_pass": db_pass
                }
                save_keys(keys)
                return key
    
    # Generate a random 32-byte hex string
    new_key = "gbl-" + secrets.token_hex(32)
    
    keys[new_key] = {
        "end_user": end_user,
        "brands": {
            brand_id: {
                "db_user": db_user,
                "db_pass": db_pass
            }
        },
        "created_at": now.isoformat(),
        "expires_at": expires.isoformat()
    }
    save_keys(keys)
    return new_key

def revoke_api_key(end_user: str, db_user: str) -> bool:
    keys = load_keys()
    
    for key, data in list(keys.items()):
        if isinstance(data, dict):
            target = data.get("end_user") or data.get("db_user")
            if target == end_user:
                data = _migrate_key_to_brands(data)
                
                # Look for the db_user in the nested brands
                brand_to_remove = None
                for b_id, b_data in data.get("brands", {}).items():
                    if b_data.get("db_user") == db_user:
                        brand_to_remove = b_id
                        break
                
                if brand_to_remove:
                    del data["brands"][brand_to_remove]
                    if not data["brands"]:
                        # If no brands left, revoke the entire key
                        del keys[key]
                    save_keys(keys)
                    return True
    return False

def revoke_all_by_email(email: str) -> bool:
    keys = load_keys()
    key_to_remove = None
    for key, data in keys.items():
        if isinstance(data, dict) and data.get("end_user") == email:
            key_to_remove = key
            break
    if key_to_remove:
        del keys[key_to_remove]
        save_keys(keys)
        return True
    return False

def revoke_brand_by_email(email: str, brand_id: str) -> bool:
    keys = load_keys()
    for key, data in list(keys.items()):
        if isinstance(data, dict) and data.get("end_user") == email:
            data = _migrate_key_to_brands(data)
            if brand_id in data.get("brands", {}):
                del data["brands"][brand_id]
                if not data["brands"]:
                    del keys[key]
                save_keys(keys)
                return True
    return False

def revalidate_api_key(end_user: str, db_user: str) -> dict | None:
    keys = load_keys()
    
    for key, data in keys.items():
        if isinstance(data, dict):
            target = data.get("end_user") or data.get("db_user")
            if target == end_user:
                data = _migrate_key_to_brands(data)
                # Check if db_user exists in any brand
                has_db_user = any(b_data.get("db_user") == db_user for b_data in data.get("brands", {}).values())
                if has_db_user:
                    now = datetime.now(timezone.utc)
                    expires = now + timedelta(days=90)
                    data["expires_at"] = expires.isoformat()
                    save_keys(keys)
                    return data
    return None

def update_db_user_password(db_user: str, new_pass: str) -> int:
    keys = load_keys()
    count = 0
    
    for key, data in keys.items():
        if isinstance(data, dict):
            data = _migrate_key_to_brands(data)
            for b_id, b_data in data.get("brands", {}).items():
                if b_data.get("db_user") == db_user:
                    b_data["db_pass"] = new_pass
                    count += 1
            
    if count > 0:
        save_keys(keys)
    return count

def update_db_user_username(old_db_user: str, new_db_user: str) -> int:
    keys = load_keys()
    count = 0
    
    for key, data in keys.items():
        if isinstance(data, dict):
            data = _migrate_key_to_brands(data)
            for b_id, b_data in data.get("brands", {}).items():
                if b_data.get("db_user") == old_db_user:
                    b_data["db_user"] = new_db_user
                    count += 1
            
    if count > 0:
        save_keys(keys)
    return count

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
    
    # Ensure nested format exists
    data = _migrate_key_to_brands(data)
    
    # Map the securely fetched credentials out, securely tying them down
    request.state.authorized_brands = data.get("brands", {})
    
    return data
