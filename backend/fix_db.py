import asyncio
from app.core.supabase_client import get_supabase_client

async def main():
    client = get_supabase_client()
    try:
        # Drop table messages since it was using wrong session_id type
        client.table("messages").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print("Cleared old messages")
    except Exception as e:
        print("Failed to clear messages:", e)

    try:
        # We need to run ALTER TABLE but we can't easily do it without postgres connection string.
        # However, we can use Supabase's REST API RPC if we created a function.
        # But we don't have a function. So let's tell the user they MUST run the SQL in Supabase Dashboard.
        pass
    except Exception as e:
        pass

if __name__ == "__main__":
    asyncio.run(main())
