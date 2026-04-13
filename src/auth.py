import json
import os
import secrets
from pathlib import Path
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

API_KEYS_FILE = Path(__file__).parent.parent / "api_keys.json"
security = HTTPBearer()

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

def generate_api_key(client_name: str) -> str:
    keys = load_keys()
    
    # Generate a random 32-byte hex string (64 characters long)
    new_key = "gbl-" + secrets.token_hex(32)
    
    keys[client_name] = new_key
    save_keys(keys)
    
    print(f"✅ Generated new API key for '{client_name}':")
    print(new_key)
    print("\nIMPORTANT: Store this key securely. It is now active.")
    return new_key

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    keys = load_keys()
    
    if token not in keys.values():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Manage MCP Server API Keys")
    parser.add_argument("command", choices=["generate"], help="Command to run")
    parser.add_argument("name", help="Name of the person/client this key is for")
    
    args = parser.parse_args()
    
    if args.command == "generate":
        generate_api_key(args.name)
