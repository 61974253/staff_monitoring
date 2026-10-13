
import os
import hmac
import hashlib
import secrets
import getpass

from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

PROJECT_DIR = Path(__file__).resolve().parent
load_dotenv(PROJECT_DIR / ".env")

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SECRET_KEY")

if not url or not key:
    raise RuntimeError("Supabase settings missing in .env")

db = create_client(url, key)

admin_id = input("Create Admin ID: ").strip()
password = getpass.getpass("Create Admin Password: ")

if len(admin_id) < 3:
    raise ValueError("Admin ID must contain at least 3 characters.")

if len(password) < 12:
    raise ValueError("Admin password must contain at least 12 characters.")

salt = secrets.token_bytes(16)
password_hash = hashlib.pbkdf2_hmac(
    "sha256",
    password.encode("utf-8"),
    salt,
    300_000
).hex()

try:
    db.table("admin_users").insert({
        "admin_id": admin_id,
        "password_salt": salt.hex(),
        "password_hash": password_hash,
        "is_active": True
    }).execute()

    print("Admin account created successfully.")

except Exception as e:
    print("Admin creation failed:", repr(e))
    print("Check Supabase permissions and whether the Admin ID exists.")
