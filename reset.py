
import os
import hmac
import hashlib
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

admin_id = input("Enter your existing Admin ID: ").strip()
new_password = getpass.getpass("Enter new password: ")
confirm_password = getpass.getpass("Confirm new password: ")

if len(new_password) < 12:
    raise ValueError("Password must contain at least 12 characters.")

if not hmac.compare_digest(new_password, confirm_password):
    raise ValueError("Passwords do not match.")

result = (
    db.table("admin_users")
    .select("admin_id")
    .eq("admin_id", admin_id)
    .limit(1)
    .execute()
)

if not result.data:
    raise ValueError("Admin ID not found. Check the ID and try again.")

salt = os.urandom(16)

password_hash = hashlib.pbkdf2_hmac(
    "sha256",
    new_password.encode("utf-8"),
    salt,
    300_000
).hex()

db.table("admin_users").update({
    "password_salt": salt.hex(),
    "password_hash": password_hash
}).eq("admin_id", admin_id).execute()

print("Admin password reset successfully!")
