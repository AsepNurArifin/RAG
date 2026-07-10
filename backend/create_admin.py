import asyncio
from app.core.auth import hash_password
import os
from supabase import create_client
from app.core.config import settings

async def main():
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    email = "admin@perusahaan.com"
    password = "Admin123!"
    
    # Check if exists
    existing = client.table("users").select("id").eq("email", email).execute()
    
    data = {
        "email": email,
        "password_hash": hash_password(password),
        "full_name": "Super Admin",
        "role": "admin",
        "is_active": True
    }
    
    if existing.data:
        client.table("users").update(data).eq("email", email).execute()
        print("Admin user updated!")
    else:
        client.table("users").insert(data).execute()
        print("Admin user created!")

if __name__ == "__main__":
    asyncio.run(main())
