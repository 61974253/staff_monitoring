import os
import sys
import getpass
import dotenv
from pwdlib import PasswordHash
import supabase

# Load environment variables
backend_env = os.path.join(os.path.dirname(__file__), "backend", ".env")
if os.path.exists(backend_env):
    dotenv.load_dotenv(backend_env)
else:
    dotenv.load_dotenv(".env")

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    print("Error: SUPABASE_URL and SUPABASE_KEY must be configured in backend/.env")
    sys.exit(1)

client = supabase.create_client(url, key)
password_hasher = PasswordHash.recommended()


def reset_password(admin_id: str, new_password: str):
    admin_id = admin_id.strip().lower()
    new_hash = password_hasher.hash(new_password)

    # Check if admin exists
    res = client.table("admin_users").select("admin_id").eq("admin_id", admin_id).execute()
    if not res.data:
        # Check by user_id
        res2 = client.table("admin_users").select("admin_id").eq("user_id", admin_id).execute()
        if not res2.data:
            print(f"Error: Admin '{admin_id}' not found in admin_users table.")
            return False

    update_res = client.table("admin_users").update({
        "password_hash": new_hash,
        "password_salt": "argon2-managed",
        "is_active": True
    }).eq("admin_id", admin_id).execute()

    print(f"Success! Password for admin '{admin_id}' has been updated.")
    return True


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        target_admin = sys.argv[1]
        target_pwd = sys.argv[2]
    elif len(sys.argv) == 2:
        target_admin = sys.argv[1]
        target_pwd = getpass.getpass(f"Enter new password for '{target_admin}': ")
    else:
        target_admin = input("Enter admin ID [default: ihc001]: ").strip() or "ihc001"
        target_pwd = getpass.getpass(f"Enter new password for '{target_admin}': ")

    reset_password(target_admin, target_pwd)
