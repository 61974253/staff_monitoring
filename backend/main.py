
import os
import re
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from pwdlib import PasswordHash
from supabase import create_client, Client


# --------------------------------------------------
# 1. CONFIGURATION
# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
JWT_SECRET = os.getenv("JWT_SECRET")
ADMIN_SETUP_KEY = os.getenv("ADMIN_SETUP_KEY")

missing = [
    key
    for key, value in {
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_KEY": SUPABASE_KEY,
        "JWT_SECRET": JWT_SECRET,
        "ADMIN_SETUP_KEY": ADMIN_SETUP_KEY,
    }.items()
    if not value
]

if missing:
    raise RuntimeError(
        "Missing environment variables: " + ", ".join(missing)
    )

if len(JWT_SECRET) < 10 or len(ADMIN_SETUP_KEY) < 10:
    raise RuntimeError(
        "Use separate random secrets of at least 10 characters"
    )

db: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Create the FastAPI application only once
app = FastAPI(title="Attendance Monitoring API")

password_hasher = PasswordHash.recommended()
JWT_ALGORITHM = "HS256"
TOKEN_MINUTES = 30


# --------------------------------------------------
# 2. REQUEST MODELS
# --------------------------------------------------

class FirstAdmin(BaseModel):
    setup_key: str
    user_id: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=5, max_length=50)


class LoginData(BaseModel):
    user_id: str
    password: str


class NewEmployee(BaseModel):
    user_id: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=5, max_length=50)


class UpdateRole(BaseModel):
    user_id: str
    role: str


class MonitoringEvent(BaseModel):
    event: str = Field(min_length=1, max_length=100)
    timestamp: datetime | None = None
    details: dict = Field(default_factory=dict)


# --------------------------------------------------
# 3. HELPER FUNCTIONS
# --------------------------------------------------

def clean_user_id(value: str) -> str:
    value = value.strip().lower()

    if not re.fullmatch(r"[a-z0-9._-]{3,50}", value):
        raise HTTPException(
            status_code=400,
            detail="User ID must use 3-50 letters, numbers, dot, _ or -"
        )

    return value


def create_token(user: dict) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": user["user_id"],
        "role": user["role"],
        "iat": now,
        "exp": now + timedelta(minutes=TOKEN_MINUTES),
    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )


def find_user(user_id: str):
    user_id = user_id.strip().lower()

    # Check admin account
    admin_result = (
        db.table("admin_users")
        .select("admin_id,full_name,password_hash,role,is_active")
        .eq("admin_id", user_id)
        .limit(1)
        .execute()
    )

    if admin_result.data:
        row = admin_result.data[0]

        return {
            "user_id": row["admin_id"],
            "full_name": row["full_name"],
            "password_hash": row["password_hash"],
            "role": row["role"],
            "is_active": row["is_active"],
        }

    # Check employee account
    employee_result = (
        db.table("employee_login_users")
        .select("user_id,full_name,password_hash,role,is_active")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    if employee_result.data:
        row = employee_result.data[0]

        return {
            "user_id": row["user_id"],
            "full_name": row["full_name"],
            "password_hash": row["password_hash"],
            "role": row["role"],
            "is_active": row["is_active"],
        }

    return None


# --------------------------------------------------
# 4. AUTHENTICATION
# --------------------------------------------------

def current_user(authorization: str = Header(default="")):
    scheme, _, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=401,
            detail="Login required. Please login again."
        )

    try:
        claims = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token. Please login again."
        )

    user = find_user(claims.get("sub", ""))

    if not user or not user["is_active"]:
        raise HTTPException(
            status_code=401,
            detail="User is inactive or unavailable"
        )

    return user


def require_admin(user=Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return user


# --------------------------------------------------
# 5. HEALTH CHECK
# --------------------------------------------------

@app.get("/")
def health():
    return {"status": "Attendance API running"}


# --------------------------------------------------
# 6. CREATE FIRST ADMIN
# --------------------------------------------------

@app.post("/setup/first-admin")
def setup_first_admin(data: FirstAdmin):
    if data.setup_key != ADMIN_SETUP_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid setup key"
        )

    user_id = clean_user_id(data.user_id)

    try:
        existing = (
            db.table("admin_users")
            .select("admin_id")
            .limit(1)
            .execute()
        )

        if existing.data:
            raise HTTPException(
                status_code=409,
                detail="An admin already exists"
            )

        db.table("admin_users").insert({
            "admin_id": user_id,
            "password_salt": "argon2-managed",
            "password_hash": password_hasher.hash(data.password),
            "full_name": data.full_name.strip(),
            "role": "admin",
            "is_active": True,
        }).execute()

        return {
            "message": "First admin created successfully",
            "user_id": user_id
        }

    except HTTPException:
        raise
    except Exception as exc:
        print("ADMIN SETUP ERROR:", repr(exc))
        raise HTTPException(
            status_code=500,
            detail="Admin setup failed. Check backend terminal."
        )


# --------------------------------------------------
# 7. LOGIN
# --------------------------------------------------

@app.post("/login")
def login(data: LoginData):
    try:
        user_id = clean_user_id(data.user_id)
        user = find_user(user_id)

        if not user or not user["is_active"]:
            raise HTTPException(
                status_code=401,
                detail="Invalid user ID or password"
            )

        try:
            password_ok = password_hasher.verify(
                data.password,
                user["password_hash"]
            )
        except Exception as exc:
            print("PASSWORD VERIFY ERROR:", repr(exc))
            password_ok = False

        if not password_ok:
            raise HTTPException(
                status_code=401,
                detail="Invalid user ID or password"
            )

        return {
            "access_token": create_token(user),
            "token_type": "bearer",
            "user_id": user["user_id"],
            "full_name": user["full_name"],
            "role": user["role"],
        }

    except HTTPException:
        raise
    except Exception as exc:
        print("LOGIN ERROR:", repr(exc))
        raise HTTPException(
            status_code=500,
            detail="Login failed. Check backend terminal."
        )


# --------------------------------------------------
# 8. CREATE EMPLOYEE
# --------------------------------------------------

@app.post("/admin/users")
def create_employee(
    data: NewEmployee,
    admin=Depends(require_admin)
):
    user_id = clean_user_id(data.user_id)
    full_name = data.full_name.strip()

    try:
        existing = (
            db.table("employee_login_users")
            .select("user_id")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        if existing.data:
            raise HTTPException(
                status_code=409,
                detail="Employee ID already exists"
            )

        db.table("employee_login_users").insert({
            "username": user_id,
            "password_salt": "argon2-managed",
            "password_hash": password_hasher.hash(data.password),
            "is_active": True,
            "user_id": user_id,
            "full_name": full_name,
            "role": "employee",
        }).execute()

        return {
            "message": "Employee created successfully",
            "user_id": user_id,
        }

    except HTTPException:
        raise
    except Exception as exc:
        print("CREATE EMPLOYEE ERROR:", repr(exc))

        error_text = str(exc).lower()

        if (
            "23505" in error_text
            or "duplicate" in error_text
            or "unique" in error_text
        ):
            raise HTTPException(
                status_code=409,
                detail="Employee ID already exists"
            )

        raise HTTPException(
            status_code=500,
            detail="Could not create employee. Check database columns."
        )


# --------------------------------------------------
# 9. VIEW ALL EMPLOYEES
# --------------------------------------------------

@app.get("/admin/users")
def get_all_employees(admin=Depends(require_admin)):
    try:
        response = (
            db.table("employee_login_users")
            .select("user_id,full_name,role,is_active")
            .order("user_id")
            .execute()
        )

        return {"users": response.data or []}

    except Exception as exc:
        print("GET EMPLOYEES ERROR:", repr(exc))
        raise HTTPException(
            status_code=500,
            detail="Could not load employees"
        )


# --------------------------------------------------
# 10. EMPLOYEE ATTENDANCE
# --------------------------------------------------

@app.get("/admin/users/{user_id}/attendance")
def get_employee_attendance(
    user_id: str,
    admin=Depends(require_admin)
):
    try:
        employee_response = (
            db.table("employee_login_users")
            .select("user_id,full_name,role,is_active")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        if not employee_response.data:
            raise HTTPException(
                status_code=404,
                detail="Employee not found"
            )

        employee = employee_response.data[0]

        attendance_response = (
            db.table("employee_attendance")
            .select("attendance_in,attendance_out")
            .eq("username", user_id)
            .execute()
        )

        return {
            "employee": employee,
            "attendance": attendance_response.data or []
        }

    except HTTPException:
        raise
    except Exception as exc:
        print("EMPLOYEE ATTENDANCE ERROR:", repr(exc))
        raise HTTPException(
            status_code=500,
            detail="Could not load employee attendance"
        )


# --------------------------------------------------
# 11. UPDATE USER ROLE
# --------------------------------------------------

@app.put("/admin/users/role")
def update_user_role(
    data: UpdateRole,
    admin=Depends(require_admin)
):
    user_id = clean_user_id(data.user_id)
    new_role = data.role.strip().lower()

    if new_role not in ("admin", "employee"):
        raise HTTPException(
            status_code=400,
            detail="Role must be admin or employee"
        )

    if user_id == admin["user_id"] and new_role != "admin":
        raise HTTPException(
            status_code=409,
            detail="You cannot demote your own admin account"
        )

    try:
        target = find_user(user_id)

        if not target:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        if target["role"] == "admin" and new_role != "admin":
            admins = (
                db.table("admin_users")
                .select("admin_id")
                .execute()
                .data or []
            )

            if len(admins) <= 1:
                raise HTTPException(
                    status_code=409,
                    detail="Cannot demote the last admin"
                )

        admin_ids = [
            row["admin_id"]
            for row in (
                db.table("admin_users")
                .select("admin_id")
                .execute()
                .data or []
            )
        ]

        if user_id in admin_ids:
            db.table("admin_users").update({
                "role": new_role
            }).eq("admin_id", user_id).execute()
        else:
            db.table("employee_login_users").update({
                "role": new_role
            }).eq("user_id", user_id).execute()

        return {
            "message": f"User {user_id} role updated to {new_role}",
            "user_id": user_id,
            "role": new_role,
        }

    except HTTPException:
        raise
    except Exception as exc:
        print("ROLE UPDATE ERROR:", repr(exc))
        raise HTTPException(
            status_code=500,
            detail="Could not update user role"
        )


# --------------------------------------------------
# 12. CURRENT USER PROFILE
# --------------------------------------------------

@app.get("/me")
def my_profile(user=Depends(current_user)):
    return {
        "user_id": user["user_id"],
        "full_name": user["full_name"],
        "role": user["role"],
    }


# --------------------------------------------------
# 13. SAVE EMPLOYEE MONITORING EVENTS
# --------------------------------------------------

@app.post("/employee/monitoring-events")
def save_monitoring_event(
    data: MonitoringEvent,
    user=Depends(current_user)
):
    # Only authenticated employees may upload events
    if user["role"] != "employee":
        raise HTTPException(
            status_code=403,
            detail="Employee access required"
        )

    event_name = data.event.strip()

    if not event_name:
        raise HTTPException(
            status_code=400,
            detail="Event name is required"
        )

    event_time = data.timestamp or datetime.now(timezone.utc)

    record = {
        "employee_user_id": str(user["user_id"]),
        "event_name": event_name,
        "event_timestamp": event_time.isoformat(),
        "details": data.details,
    }

    try:
        response = (
            db.table("employee_monitoring_logs")
            .insert(record)
            .execute()
        )

        return {
            "message": "Event saved",
            "data": response.data or []
        }

    except Exception as exc:
        print("SAVE MONITORING EVENT ERROR:", repr(exc))
        raise HTTPException(
            status_code=500,
            detail=(
                "Could not save monitoring event. "
                "Check backend terminal and Supabase table columns."
            )
        )


# --------------------------------------------------
# 14. VIEW MONITORING LOGS - ADMIN ONLY
# --------------------------------------------------

@app.get("/admin/monitoring-logs")
def get_monitoring_logs(admin=Depends(require_admin)):
    try:
        response = (
            db.table("employee_monitoring_logs")
            .select(
                "id,employee_user_id,event_name,"
                "event_timestamp,details,created_at"
            )
            .order("event_timestamp", desc=True)
            .limit(200)
            .execute()
        )

        return {"logs": response.data or []}

    except Exception as exc:
        print("GET MONITORING LOGS ERROR:", repr(exc))
        raise HTTPException(
            status_code=500,
            detail=(
                "Could not load monitoring logs. "
                "Check backend terminal and Supabase table columns."
            )
        )
