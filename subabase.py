
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

print("URL configured:", bool(url))
print("Key configured:", bool(key))
print("Key type:", (
    "publishable"
    if key and key.startswith("sb_publishable_")
    else "legacy anon or other key"
))

supabase = create_client(url, key)

try:
    result = supabase.table("employees").select(
        "employee_id"
    ).limit(1).execute()

    print("Supabase query successful!")
    print("Rows returned:", len(result.data))
    print(result.data)

except Exception as error:
    print("Query failed:")
    print(error)
