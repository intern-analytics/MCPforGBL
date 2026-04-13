import json
import os
import secrets
from pathlib import Path
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

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

def revoke_api_key(client_name: str):
    keys = load_keys()
    if client_name in keys:
        del keys[client_name]
        save_keys(keys)
        print(f"❌ Revoked API key for '{client_name}'. Access is now denied.")
    else:
        print(f"⚠️  No API key found for '{client_name}'.")

async def verify_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    # 1. Try to get token from Authorization header
    token = None
    if credentials:
        token = credentials.credentials
    
    # 2. If not in header, look in the URL (?token=...)
    if not token:
        token = request.query_params.get("token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
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
    parser.add_argument("command", choices=["generate", "revoke", "list"], help="Command to run")
    parser.add_argument("name", nargs="?", help="Name of the person/client this key is for")
    
    args = parser.parse_args()
    
    if args.command == "generate":
        if not args.name:
            print("Error: 'generate' requires a name.")
        else:
            generate_api_key(args.name)
    elif args.command == "revoke":
        if not args.name:
            print("Error: 'revoke' requires a name.")
        else:
            revoke_api_key(args.name)
    elif args.command == "list":
        keys = load_keys()
        if not keys:
            print("No keys found.")
        else:
            print("\nActive API Keys:")
            for name, key in keys.items():
                # Show only first 8 chars for security
                print(f"  {name}: {key[:12]}...")
