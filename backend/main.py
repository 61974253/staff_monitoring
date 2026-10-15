
import os
import re
from datetime import datetime, timedelta, timezone

from fastapi.responses import FileResponse
import jwt
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from pwdlib import PasswordHash
from supabase import create_client, Client
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials




# --------------------------------------------------
# 1. CONFIGURATION
# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
if SUPABASE_URL.endswith("/rest/v1"):
    SUPABASE_URL = SUPABASE_URL[:-len("/rest/v1")]
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_SECRET_KEY")
)
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
privileged_db: Client | None = (
    create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    if SUPABASE_SERVICE_ROLE_KEY
    else None
)

# Create the FastAPI application only once
app = FastAPI(title="Attendance Monitoring API")
# Enable Bearer token authentication in Swagger
bearer_scheme = HTTPBearer()
WEB_ADMIN_DIR = Path(__file__).parent / "web_admin"
app.mount("/web_admin", StaticFiles(directory=WEB_ADMIN_DIR), name="web_admin")

password_hasher = PasswordHash.recommended()
JWT_ALGORITHM = "HS256"
ADMIN_TOKEN_MINUTES = 30
EMPLOYEE_TOKEN_MINUTES = 12 * 60


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


class BreakSession(BaseModel):
    break_start: datetime
    break_end: datetime
    break_reason: str = Field(min_length=1, max_length=100)
    break_type: str = Field(default="personal", min_length=1, max_length=50)


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
    token_minutes = (
        EMPLOYEE_TOKEN_MINUTES
        if user["role"] == "employee"
        else ADMIN_TOKEN_MINUTES
    )

    payload = {
        "sub": user["user_id"],
        "role": user["role"],
        "iat": now,
        "exp": now + timedelta(minutes=token_minutes),
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


def get_privileged_db() -> Client:
    if privileged_db is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Employee attendance and break-session writes need "
                "SUPABASE_SERVICE_ROLE_KEY in backend/.env"
            )
        )

    return privileged_db



def start_employee_attendance(user: dict) -> None:


    attendance_db = get_privileged_db()

    # Find the employee record
    employee_response = (
        attendance_db.table("employees")
        .select("id")
        .eq("employee_id", user["user_id"])
        .limit(1)
        .execute()
    )

    if employee_response.data:
        employee_id = employee_response.data[0]["id"]
    else:
        # Create employee record if it does not exist
        attendance_db.table("employees").insert({
            "employee_id": user["user_id"],
            "employee_name": user["full_name"],
            "role": "employee",
            "is_active": True,
        }).execute()

        employee_response = (
            attendance_db.table("employees")
            .select("id")
            .eq("employee_id", user["user_id"])
            .limit(1)
            .execute()
        )

        if not employee_response.data:
            raise RuntimeError(
                f"Could not find employee record for {user['user_id']}"
            )

        employee_id = employee_response.data[0]["id"]

    attendance_sessions = attendance_db.table("attendance_sessions")

    # Check whether the employee already has an open session
    open_session = (
        attendance_sessions
        .select("id")
        .eq("employee_id", employee_id)
        .is_("logout_time", "null")
        .limit(1)
        .execute()
    )

    # Do not create duplicate open attendance sessions
    if open_session.data:
        return

    # Save login time and Present status
    now = datetime.now(timezone.utc).isoformat()

    attendance_sessions.insert({
        "employee_id": employee_id,
        "login_time": now,
        "logout_time": None,
        "status": "Present",
        "total_hours": 0,
    }).execute()


# --------------------------------------------------
# 4. AUTHENTICATION
# --------------------------------------------------


def current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
):
    token = credentials.credentials

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


@app.get("/admin")
def open_admin_panel():
    return FileResponse(WEB_ADMIN_DIR / "index.html")


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

@app.post("/admin/login")
def admin_login(data: LoginData):
    try:
        user_id = clean_user_id(data.user_id)
        user = find_user(user_id)

        if not user or not user["is_active"]:
            raise HTTPException(
                status_code=401,
                detail="Invalid admin ID or password"
            )

        try:
            password_ok = password_hasher.verify(
                data.password,
                user["password_hash"]
            )
        except Exception as exc:
            print("PASSWORD VERIFY ERROR:", repr(exc))
            password_ok = False

        if not password_ok or user["role"] != "admin":
            raise HTTPException(
                status_code=401,
                detail="Invalid admin ID or password"
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
        print("ADMIN LOGIN ERROR:", repr(exc))
        raise HTTPException(
            status_code=500,
            detail="Admin login failed. Check backend terminal."
        )


@app.get("/health")
def health_check():
    return {"status": "connected"}

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

        # Save attendance after successful employee login
        if user["role"] == "employee":
            print(
                "DEBUG: Employee login successful:",
                user["user_id"]
            )

            start_employee_attendance(user)

            print("DEBUG: Attendance function completed")

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
    

@app.post("/logout")
def logout(user=Depends(current_user)):
    try:
        # Only employee accounts can close employee attendance
        if user["role"] != "employee":
            raise HTTPException(
                status_code=403,
                detail="Only employees can logout"
            )

        attendance_db = get_privileged_db()

        # Find the employee database ID
        employee_response = (
            attendance_db.table("employees")
            .select("id")
            .eq("employee_id", user["user_id"])
            .limit(1)
            .execute()
        )

        if not employee_response.data:
            raise HTTPException(
                status_code=404,
                detail="Employee record not found"
            )

        employee_id = employee_response.data[0]["id"]

        # Find the latest attendance session that has not been closed
        session_response = (
            attendance_db.table("attendance_sessions")
            .select("id, login_time")
            .eq("employee_id", employee_id)
            .is_("logout_time", "null")
            .order("login_time", desc=True)
            .limit(1)
            .execute()
        )

        if not session_response.data:
            raise HTTPException(
                status_code=404,
                detail="No active attendance session found"
            )

        session = session_response.data[0]

        # Convert the stored login timestamp into a datetime
        login_dt = datetime.fromisoformat(
            session["login_time"].replace("Z", "+00:00")
        )

        # Record the exact logout time in UTC
        logout_dt = datetime.now(timezone.utc)

        # Calculate elapsed seconds from login to logout
        total_seconds = max(
            0,
            int((logout_dt - login_dt).total_seconds())
        )

        # Store total elapsed hours as a decimal number
        total_hours = round(total_seconds / 3600, 6)

        # Format duration for display as HH:MM:SS
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        total_duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        # Save logout time, duration, and final status
        update_response = (
            attendance_db.table("attendance_sessions")
            .update({
                "logout_time": logout_dt.isoformat(),
                "total_hours": total_hours,
                "status": "Logged Out",
            })
            .eq("id", session["id"])
            .execute()
        )

        if not update_response.data:
            raise RuntimeError("Attendance session was not updated")

        # Return the completed attendance details
        return {
            "message": "Logout successful",
            "user_id": user["user_id"],
            "login_time": session["login_time"],
            "logout_time": logout_dt.isoformat(),
            "total_hours": total_hours,
            "total_duration": total_duration,
            "status": "Logged Out",
        }

    except HTTPException:
        raise

    except Exception as exc:
        print("LOGOUT ERROR:", repr(exc))
        raise HTTPException(
            status_code=500,
            detail="Logout failed. Check backend terminal."
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
    user_id = clean_user_id(user_id)

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
        attendance_db = get_privileged_db()
        attendance_employee_response = (
            attendance_db.table("employees")
            .select("id,employee_name,role,is_active")
            .eq("employee_id", user_id)
            .limit(1)
            .execute()
        )

        attendance = []
        if attendance_employee_response.data:
            attendance_employee = attendance_employee_response.data[0]
            page_size = 1000
            offset = 0
            while True:
                attendance_response = (
                    attendance_db.table("attendance_sessions")
                    .select("id,login_time,logout_time,total_hours,status")
                    .eq("employee_id", attendance_employee["id"])
                    .order("login_time", desc=True)
                    .range(offset, offset + page_size - 1)
                    .execute()
                )
                page = attendance_response.data or []
                attendance.extend(page)
                if len(page) < page_size:
                    break
                offset += page_size

        page_size = 1000
        offset = 0
        logs = []
        while True:
            logs_response = (
                db.table("employee_monitoring_logs")
                .select(
                    "id,employee_user_id,event_name,event_timestamp,"
                    "details,break_sessions,created_at"
                )
                .eq("employee_user_id", user_id)
                .order("event_timestamp", desc=True)
                .range(offset, offset + page_size - 1)
                .execute()
            )
            page = logs_response.data or []
            logs.extend(page)
            if len(page) < page_size:
                break
            offset += page_size

        def parse_event_time(value: str) -> datetime | None:
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed.astimezone(timezone.utc)
            except (AttributeError, TypeError, ValueError):
                return None

        activity_logs = [
            log for log in logs
            if log.get("event_name") in ("SESSION_SUMMARY", "IDLE_SESSION")
        ]

        attendance_with_activity = []
        for session in attendance:
            login_time = parse_event_time(session.get("login_time"))
            logout_time = parse_event_time(session.get("logout_time") or "")
            session_end = logout_time or datetime.now(timezone.utc)
            idle_summaries_by_time = {}
            idle_intervals = []

            for activity in activity_logs:
                activity_time = parse_event_time(
                    activity.get("event_timestamp")
                )
                if (
                    login_time is not None
                    and activity_time is not None
                    and login_time <= activity_time <= session_end
                ):
                    details = activity.get("details")
                    if not isinstance(details, dict):
                        continue

                    if activity.get("event_name") == "SESSION_SUMMARY":
                        idle = details.get("idle_seconds", 0)
                        try:
                            idle = max(0, int(idle))
                        except (TypeError, ValueError):
                            idle = 0

                        summary_time = activity_time.replace(microsecond=0)
                        idle_summaries_by_time[summary_time] = max(
                            idle,
                            idle_summaries_by_time.get(summary_time, 0)
                        )
                    elif activity.get("event_name") == "IDLE_SESSION":
                        idle_start = parse_event_time(details.get("idle_start"))
                        idle_end = parse_event_time(details.get("idle_end"))
                        if idle_start is not None and idle_end is not None:
                            clipped_start = max(login_time, idle_start)
                            clipped_end = min(session_end, idle_end)
                            if clipped_end > clipped_start:
                                idle_intervals.append(
                                    (clipped_start, clipped_end)
                                )
            session_with_activity = dict(session)
            merged_idle_intervals = []
            for start, end in sorted(idle_intervals):
                if (
                    merged_idle_intervals
                    and start <= merged_idle_intervals[-1][1]
                ):
                    previous_start, previous_end = merged_idle_intervals[-1]
                    merged_idle_intervals[-1] = (
                        previous_start,
                        max(previous_end, end)
                    )
                else:
                    merged_idle_intervals.append((start, end))

            idle_seconds = sum(
                int((end - start).total_seconds())
                for start, end in merged_idle_intervals
            )
            if not merged_idle_intervals:
                idle_seconds = sum(idle_summaries_by_time.values())

            if login_time is not None:
                attendance_seconds = max(
                    0,
                    int((session_end - login_time).total_seconds())
                )
                idle_seconds = min(idle_seconds, attendance_seconds)
                active_seconds = max(0, attendance_seconds - idle_seconds)
            else:
                active_seconds = 0

            session_with_activity["active_seconds"] = active_seconds
            session_with_activity["idle_seconds"] = idle_seconds
            attendance_with_activity.append(session_with_activity)

        return {
            "employee": employee,
            "attendance": attendance_with_activity,
            "logs": logs,
        }

    except HTTPException:
        raise
    except Exception as exc:
        print("EMPLOYEE ATTENDANCE ERROR:", repr(exc))
        raise HTTPException(
            status_code=500,
            detail="Could not load employee details"
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




@app.post("/employee/employee-break-sessions")
def save_break_session(
    data: BreakSession,
    user=Depends(current_user)
):
    # Only employees can save break sessions
    if user["role"] != "employee":
        raise HTTPException(
            status_code=403,
            detail="Employee access required"
        )

    # Validate break duration
    if data.break_end < data.break_start:
        raise HTTPException(
            status_code=400,
            detail="Break end must be at or after break start"
        )

    # Prepare the break-session details
    event_name = "break_session"

    record = {
    "employee_user_id": str(user["user_id"]),
    "event_name": "BREAK_SESSION",
    "event_timestamp": data.break_start.isoformat(),
    "break_sessions": {
        "break_start": data.break_start.isoformat(),
        "break_end": data.break_end.isoformat(),
        "break_reason": data.break_reason.strip(),
        "break_type": data.break_type.strip(),
    }
}

    # Validate required text fields
    if not record["break_sessions"]["break_reason"] or not record["break_sessions"]["break_type"]:
        raise HTTPException(
            status_code=400,
            detail="Break reason and break type are required"
        )

    try:
        # Save the break session in the monitoring logs table
        response = (
            get_privileged_db()
            .table("employee_monitoring_logs")
            .insert(record)
            .execute()
        )

        return {
            "message": "Break session saved successfully",
            "data": response.data or []
        }

    except Exception as exc:
        print("SAVE BREAK SESSION ERROR:", repr(exc))
        raise HTTPException(
            status_code=500,
            detail="Could not save break session. Check backend terminal."
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
                "event_timestamp,details,created_at,break_sessions"
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
