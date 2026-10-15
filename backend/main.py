
import hashlib
import hmac
import os
import re
import secrets
import smtplib
import time
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi.responses import FileResponse
import jwt
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import HTMLResponse
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

app = FastAPI(title="Attendance Monitoring API")
<<<<<<< HEAD
# Enable Bearer token authentication in Swagger
bearer_scheme = HTTPBearer()
WEB_ADMIN_DIR = Path(__file__).parent / "web_admin"
app.mount("/web_admin", StaticFiles(directory=WEB_ADMIN_DIR), name="web_admin")

=======
>>>>>>> 5a595d8 (feat: enhance admin web dashboard, employee monitoring, and remove id column dependencies)
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


class AdminForgotPasswordRequest(BaseModel):
    admin_id: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=5, max_length=150)


class AdminResetPasswordVerify(BaseModel):
    admin_id: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=5, max_length=150)
    otp: str = Field(min_length=4, max_length=10)
    new_password: str = Field(min_length=5, max_length=50)


class UpdateRole(BaseModel):
    user_id: str
    role: str


class MonitoringEvent(BaseModel):
    event: str = Field(min_length=1, max_length=100)
    timestamp: datetime | None = None
    details: dict = Field(default_factory=dict)


<<<<<<< HEAD
class BreakSession(BaseModel):
    break_start: datetime
    break_end: datetime
    break_reason: str = Field(min_length=1, max_length=100)
    break_type: str = Field(default="personal", min_length=1, max_length=50)
=======
class LeaveRequestData(BaseModel):
    leave_date: str = Field(min_length=4, max_length=50)
    leave_type: str = Field(default="Casual Leave", max_length=50)
    reason: str = Field(min_length=1, max_length=1000)


class CancelAttemptData(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    details: dict = Field(default_factory=dict)


class LeaveDecisionData(BaseModel):
    employee_id: str | None = None
    leave_date: str | None = None
    decision: str = Field(min_length=1, max_length=20)
    comments: str = Field(default="", max_length=500)
>>>>>>> 5a595d8 (feat: enhance admin web dashboard, employee monitoring, and remove id column dependencies)


# --------------------------------------------------
# 3. HELPERS
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

    admin_result = (
        db.table("admin_users")
        .select("admin_id,full_name,password_hash,role,is_active")
        .eq("admin_id", user_id)
        .limit(1)
        .execute()
    )

    if not admin_result.data:
        try:
            admin_result = (
                db.table("admin_users")
                .select("admin_id,full_name,password_hash,role,is_active")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
        except Exception:
            pass

    if admin_result.data:
        row = admin_result.data[0]
        return {
            "user_id": row["admin_id"],
            "full_name": row["full_name"],
            "password_hash": row["password_hash"],
            "role": row["role"],
            "is_active": row["is_active"],
        }

    employee_result = (
        db.table("employee_login_users")
        .select("user_id,username,full_name,password_hash,role,is_active")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    if not employee_result.data:
        employee_result = (
            db.table("employee_login_users")
            .select("user_id,username,full_name,password_hash,role,is_active")
            .eq("username", user_id)
            .limit(1)
            .execute()
        )

    if employee_result.data:
        row = employee_result.data[0]
        return {
            "user_id": row["user_id"] or row.get("username") or user_id,
            "full_name": row["full_name"],
            "password_hash": row["password_hash"],
            "role": row["role"],
            "is_active": row["is_active"],
        }

    return None


<<<<<<< HEAD
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

=======
def current_user(authorization: str = Header(default="")):
    scheme, _, token = authorization.partition(" ")
>>>>>>> 5a595d8 (feat: enhance admin web dashboard, employee monitoring, and remove id column dependencies)

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
# 4. HEALTH CHECK
# --------------------------------------------------

@app.get("/")
def health():
    return {"status": "Attendance API running"}


<<<<<<< HEAD
@app.get("/admin")
def open_admin_panel():
    return FileResponse(WEB_ADMIN_DIR / "index.html")
=======
@app.get("/admin", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
def get_admin_dashboard_page():
    html_file = os.path.join(BASE_DIR, "admin_dashboard.html")
    if os.path.exists(html_file):
        with open(html_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Admin Dashboard template not found</h1>"
>>>>>>> 5a595d8 (feat: enhance admin web dashboard, employee monitoring, and remove id column dependencies)


# --------------------------------------------------
# 5. CREATE FIRST ADMIN
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
# 6. LOGIN
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

        password_ok = False
        stored_hash = user.get("password_hash") or ""
        stored_salt = user.get("password_salt") or ""

        # 1. Try modern Argon2 hasher
        try:
            password_ok = password_hasher.verify(
                data.password,
                stored_hash
            )
        except Exception:
            password_ok = False

        # 2. Try PBKDF2-HMAC-SHA256 fallback (used by admin.py)
        if not password_ok and stored_salt:
            try:
                salt_bytes = bytes.fromhex(stored_salt)
                calc = hashlib.pbkdf2_hmac(
                    "sha256",
                    data.password.encode("utf-8"),
                    salt_bytes,
                    300_000
                ).hex()
                if hmac.compare_digest(calc, stored_hash):
                    password_ok = True
            except Exception:
                pass

        # 3. Try legacy SHA-256 fallback
        if not password_ok and stored_salt:
            try:
                calc = hashlib.sha256((stored_salt + data.password).encode("utf-8")).hexdigest()
                if hmac.compare_digest(calc, stored_hash):
                    password_ok = True
            except Exception:
                pass

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
# 6.1 ADMIN FORGOT PASSWORD (EMAIL OTP)
# --------------------------------------------------

ADMIN_RESET_OTPS = {}

def send_admin_reset_email(to_email: str, admin_id: str, otp: str) -> bool:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT") or 587)
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    smtp_from = os.getenv("SMTP_FROM") or smtp_user or "noreply@staffmonitoring.com"

    # Log clearly in backend terminal for immediate testing and verification
    print("\n" + "=" * 60)
    print("[ADMIN PASSWORD RESET - EMAIL VERIFICATION OTP]")
    print(f"Target Admin : {admin_id}")
    print(f"Target Email : {to_email}")
    print(f"OTP Code     : {otp} (Valid for 10 minutes)")
    print("=" * 60 + "\n")

    if not smtp_host or not smtp_user or not smtp_pass:
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"TCS Staff Monitoring - Admin Password Reset Code: {otp}"
        msg["From"] = smtp_from
        msg["To"] = to_email

        text = f"Hello Admin ({admin_id}),\n\nYour password reset verification code is: {otp}\n\nThis code will expire in 10 minutes.\nIf you did not request this, please ignore this email."
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; background-color: #f8fafc; padding: 20px;">
            <div style="max-width: 500px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 12px; border: 1px solid #e2e8f0;">
              <h2 style="color: #1e3a8a; margin-top: 0;">TCS Staff Monitoring</h2>
              <p style="color: #475569; font-size: 14px;">Hello Admin <strong>{admin_id}</strong>,</p>
              <p style="color: #475569; font-size: 14px;">Use the verification code below to reset your password:</p>
              <div style="background: #eff6ff; color: #1d4ed8; font-size: 32px; font-weight: bold; letter-spacing: 6px; text-align: center; padding: 16px; border-radius: 8px; margin: 20px 0;">
                {otp}
              </div>
              <p style="color: #64748b; font-size: 12px;">This code will expire in 10 minutes.<br>If you did not request a password reset, you can safely ignore this email.</p>
            </div>
          </body>
        </html>
        """
        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_from, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_from, [to_email], msg.as_string())
        return True
    except Exception as exc:
        print("SMTP SEND EMAIL ERROR:", repr(exc))
        return False


@app.post("/admin/forgot-password/request")
def request_admin_forgot_password(data: AdminForgotPasswordRequest):
    admin_id = clean_user_id(data.admin_id)
    email = data.email.strip().lower()

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise HTTPException(status_code=400, detail="Invalid email address format")

    try:
        res = db.table("admin_users").select("admin_id").eq("admin_id", admin_id).limit(1).execute()
        if not res.data:
            res = db.table("admin_users").select("admin_id").eq("user_id", admin_id).limit(1).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail=f"Admin '{admin_id}' not found")
    except HTTPException:
        raise
    except Exception as exc:
        print("ADMIN LOOKUP ERROR:", repr(exc))
        raise HTTPException(status_code=500, detail="Database lookup failed")

    # Update email column in admin_users if column exists
    try:
        db.table("admin_users").update({"email": email}).eq("admin_id", admin_id).execute()
    except Exception:
        pass

    otp = f"{secrets.randbelow(900000) + 100000}"
    ADMIN_RESET_OTPS[admin_id] = {
        "otp": otp,
        "email": email,
        "expires_at": time.time() + 600
    }

    email_sent = send_admin_reset_email(email, admin_id, otp)

    return {
        "message": f"Verification code sent to {email}",
        "admin_id": admin_id,
        "email_sent": email_sent,
        "dev_code": otp if not email_sent else None,
        "hint": "Check your email inbox or console for the 6-digit code."
    }


@app.post("/admin/forgot-password/verify-and-reset")
def verify_and_reset_admin_password(data: AdminResetPasswordVerify):
    admin_id = clean_user_id(data.admin_id)
    email = data.email.strip().lower()
    otp = data.otp.strip()

    if len(data.new_password) < 5:
        raise HTTPException(status_code=400, detail="Password must be at least 5 characters")

    record = ADMIN_RESET_OTPS.get(admin_id)
    if not record:
        raise HTTPException(status_code=400, detail="No password reset request found for this Admin ID. Please request a code first.")

    if time.time() > record["expires_at"]:
        ADMIN_RESET_OTPS.pop(admin_id, None)
        raise HTTPException(status_code=400, detail="Verification code has expired. Please request a new code.")

    if record["otp"] != otp:
        raise HTTPException(status_code=400, detail="Invalid verification code. Please check the code and try again.")

    new_hash = password_hasher.hash(data.new_password)

    try:
        db.table("admin_users").update({
            "password_hash": new_hash,
            "password_salt": "argon2-managed",
            "is_active": True
        }).eq("admin_id", admin_id).execute()

        ADMIN_RESET_OTPS.pop(admin_id, None)

        return {
            "message": f"Password for admin '{admin_id}' has been reset successfully. You can now log in."
        }
    except Exception as exc:
        print("ADMIN RESET PASSWORD UPDATE ERROR:", repr(exc))
        raise HTTPException(status_code=500, detail="Failed to update password in database")


# --------------------------------------------------
# 7. CREATE EMPLOYEE
# --------------------------------------------------

@app.post("/admin/users")
def create_employee(
    data: NewEmployee,
    admin=Depends(require_admin)
):
    user_id = clean_user_id(data.user_id)

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
            "full_name": data.full_name.strip(),
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
        raise HTTPException(
            status_code=500,
            detail="Could not create employee. Check database columns."
        )


# --------------------------------------------------
# 8. VIEW EMPLOYEES
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
# 9. EMPLOYEE ATTENDANCE
# --------------------------------------------------

def format_duration_seconds(seconds: int) -> str:
    seconds = max(0, int(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}h {m:02d}m {s:02d}s"
    elif m > 0:
        return f"{m}m {s:02d}s"
    else:
        return f"{s}s"


def format_idle_minutes(seconds: int) -> str:
    seconds = max(0, int(seconds))
    mins = seconds // 60
    rem = seconds % 60
    if mins > 0 and rem > 0:
        return f"{mins} mins {rem:02d}s"
    elif mins > 0:
        return f"{mins} mins"
    else:
        return f"{rem}s"


@app.get("/admin/users/{user_id}/attendance")
def get_employee_attendance(
    user_id: str,
    admin=Depends(require_admin)
):
    user_id = clean_user_id(user_id)

    try:
        user_id = clean_user_id(user_id)
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

<<<<<<< HEAD
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
=======
        attendance_response = (
            db.table("employee_attendance")
            .select("attendance_in,attendance_out")
            .eq("username", user_id)
            .order("attendance_in", desc=True)
            .execute()
        )

        now_dt = datetime.now(timezone.utc)
        today_str = now_dt.strftime("%Y-%m-%d")

        processed_attendance = []
        today_work_sec = 0

        for att in (attendance_response.data or []):
            att_in = att.get("attendance_in") or ""
            att_out = att.get("attendance_out") or ""
            work_sec = 0
            rec_date = ""

            if att_in:
                try:
                    in_dt = datetime.fromisoformat(att_in.replace("Z", "+00:00"))
                    rec_date = in_dt.strftime("%Y-%m-%d")
                    if att_out:
                        out_dt = datetime.fromisoformat(att_out.replace("Z", "+00:00"))
                        work_sec = max(0, int((out_dt - in_dt).total_seconds()))
                    else:
                        work_sec = max(0, int((now_dt - in_dt).total_seconds()))

                    if rec_date == today_str:
                        today_work_sec += work_sec
                except Exception:
                    pass

            processed_attendance.append({
                "date": rec_date or (att_in[:10] if len(att_in) >= 10 else ""),
                "attendance_in": att_in,
                "attendance_out": att_out,
                "work_seconds": work_sec,
                "work_formatted": format_duration_seconds(work_sec),
                "is_active": not bool(att_out),
            })

        # Load idle records (from employee_idle_logs or fallback to employee_monitoring_logs)
        idle_records = []
        try:
            idle_response = (
                db.table("employee_idle_logs")
                .select("idle_seconds,recorded_at")
                .eq("username", user_id)
                .order("recorded_at", desc=True)
                .limit(200)
                .execute()
            )
            idle_records = idle_response.data or []
        except Exception:
            pass

        if not idle_records:
            try:
                mon_res = (
                    db.table("employee_monitoring_logs")
                    .select("event_timestamp,details")
                    .eq("employee_user_id", user_id)
                    .in_("event_name", ["IDLE_ENDED", "BREAK_SESSION"])
                    .order("event_timestamp", desc=True)
                    .limit(200)
                    .execute()
                )
                for r in (mon_res.data or []):
                    det = r.get("details") or {}
                    sec = int(det.get("duration_seconds") or det.get("idle_seconds") or 0)
                    if sec > 0:
                        idle_records.append({
                            "idle_seconds": sec,
                            "recorded_at": r.get("event_timestamp"),
                        })
            except Exception:
                pass

        total_idle_sec = 0
        today_idle_sec = 0
        for ir in idle_records:
            sec = int(ir.get("idle_seconds") or 0)
            ir["duration_formatted"] = format_idle_minutes(sec)
            ir["idle_minutes"] = round(sec / 60.0, 1)
            total_idle_sec += sec
            rec_at = str(ir.get("recorded_at") or "")
            if today_str in rec_at:
                today_idle_sec += sec

        return {
            "employee": employee_response.data[0],
            "attendance": processed_attendance,
            "today_work_seconds": today_work_sec,
            "today_work_formatted": format_duration_seconds(today_work_sec),
            "today_idle_seconds": today_idle_sec,
            "today_idle_formatted": format_idle_minutes(today_idle_sec),
            "total_idle_seconds": total_idle_sec,
            "total_idle_formatted": format_idle_minutes(total_idle_sec),
            "idle_records": idle_records,
>>>>>>> 5a595d8 (feat: enhance admin web dashboard, employee monitoring, and remove id column dependencies)
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
# 10. UPDATE USER ROLE
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

        admin_rows = (
            db.table("admin_users")
            .select("admin_id")
            .execute()
            .data or []
        )

        admin_ids = [row["admin_id"] for row in admin_rows]

        if (
            user_id in admin_ids
            and new_role != "admin"
            and len(admin_ids) <= 1
        ):
            raise HTTPException(
                status_code=409,
                detail="Cannot demote the last admin"
            )

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
# 11. CURRENT USER PROFILE
# --------------------------------------------------

@app.get("/me")
def my_profile(user=Depends(current_user)):
    return {
        "user_id": user["user_id"],
        "full_name": user["full_name"],
        "role": user["role"],
    }


# --------------------------------------------------
# 12. SAVE MONITORING EVENTS + IDLE SESSIONS
# --------------------------------------------------


@app.post("/employee/monitoring-events")
def save_monitoring_event(
    data: MonitoringEvent,
    user=Depends(current_user)
):
    if user["role"] != "employee":
        raise HTTPException(
            status_code=403,
            detail="Employee access required"
        )

    event_name = data.event.strip().upper()

    if not event_name:
        raise HTTPException(
            status_code=400,
            detail="Event name is required"
        )

    user_id = str(user["user_id"])
    event_time = data.timestamp or datetime.now(timezone.utc)

    if event_time.tzinfo is None:
        event_time = event_time.replace(tzinfo=timezone.utc)
    else:
        event_time = event_time.astimezone(timezone.utc)

    record = {
        "employee_user_id": user_id,
        "event_name": event_name,
        "event_timestamp": event_time.isoformat(),
        "details": data.details or {},
    }

    try:
        # 1. Save event in employee_monitoring_logs
        log_result = (
            db.table("employee_monitoring_logs")
            .insert(record)
            .execute()
        )

        idle_action = "No idle action"

        # 2. Upload idle duration to employee_idle_logs when idle ends or break submitted
        if event_name in ("IDLE_ENDED", "BREAK_SESSION"):
            duration = int(data.details.get("duration_seconds", 0))
            if duration > 0:
                try:
                    db.table("employee_idle_logs").insert({
                        "username": user_id,
                        "idle_seconds": duration,
                        "recorded_at": event_time.isoformat(),
                    }).execute()
                    idle_action = f"Saved {duration}s idle time to employee_idle_logs"
                    print(f"SUPABASE IDLE UPLOAD: {user_id} -> {duration}s")
                except Exception as idle_err:
                    print("EMPLOYEE IDLE LOG ERROR:", repr(idle_err))
                    idle_action = f"employee_idle_logs error: {idle_err}"

        # 3. Optional: Attempt idle_sessions table (handled safely to prevent breaking API if table schema differs)
        try:
            if event_name == "IDLE_STARTED":
                existing = (
                    db.table("idle_sessions")
                    .select("user_id")
                    .eq("user_id", user_id)
                    .is_("idle_end", "null")
                    .limit(1)
                    .execute()
                )
                if not existing.data:
                    db.table("idle_sessions").insert({
                        "user_id": user_id,
                        "idle_start": event_time.isoformat(),
                    }).execute()
            elif event_name == "IDLE_ENDED":
                duration = int(data.details.get("duration_seconds", 0))
                existing = (
                    db.table("idle_sessions")
                    .select("user_id,idle_start")
                    .eq("user_id", user_id)
                    .is_("idle_end", "null")
                    .order("idle_start", desc=True)
                    .limit(1)
                    .execute()
                )
                if existing.data:
                    session = existing.data[0]
                    db.table("idle_sessions").update({
                        "idle_end": event_time.isoformat(),
                        "duration_seconds": duration,
                    }).eq("user_id", user_id).eq("idle_start", session["idle_start"]).execute()
        except Exception:
            # Safe ignore if idle_sessions table does not have user_id column
            pass

        return {
            "message": "Event saved",
            "event": event_name,
            "idle_action": idle_action,
            "data": log_result.data or [],
        }

    except Exception as exc:
        print("MONITORING SAVE ERROR:", repr(exc))
        raise HTTPException(
            status_code=500,
            detail="Monitoring or idle save failed. "
                   "Check backend terminal and Supabase columns."
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
# 13. ADMIN: VIEW MONITORING LOGS
# --------------------------------------------------

@app.get("/admin/monitoring-logs")
def get_monitoring_logs(admin=Depends(require_admin)):
    try:
        response = (
            db.table("employee_monitoring_logs")
            .select(
<<<<<<< HEAD
                "id,employee_user_id,event_name,"
                "event_timestamp,details,created_at,break_sessions"
=======
                "employee_user_id,event_name,"
                "event_timestamp,details,created_at"
>>>>>>> 5a595d8 (feat: enhance admin web dashboard, employee monitoring, and remove id column dependencies)
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
            detail="Could not load monitoring logs"
        )


# --------------------------------------------------
# 14. ADMIN: VIEW IDLE SESSIONS / IDLE LOGS
# --------------------------------------------------

@app.get("/admin/idle-sessions")
def get_idle_sessions(admin=Depends(require_admin)):
    try:
        # Load user idle records from employee_idle_logs
        response = (
            db.table("employee_idle_logs")
            .select(
                "username,idle_seconds,recorded_at"
            )
            .order("recorded_at", desc=True)
            .limit(200)
            .execute()
        )

        return {"idle_sessions": response.data or []}

    except Exception as exc:
        print("GET IDLE SESSIONS ERROR:", repr(exc))
        raise HTTPException(
            status_code=500,
            detail="Could not load idle sessions. Check Supabase table."
        )


# --------------------------------------------------
# 15. EMPLOYEE: VIEW OWN IDLE SUMMARY
# --------------------------------------------------

@app.get("/employee/my-idle")
def get_my_idle(user=Depends(current_user)):
    user_id = str(user["user_id"])
    try:
        response = (
            db.table("employee_idle_logs")
            .select("username,idle_seconds,recorded_at")
            .eq("username", user_id)
            .order("recorded_at", desc=True)
            .limit(100)
            .execute()
        )
        records = response.data or []
        total_seconds = sum(int(r.get("idle_seconds") or 0) for r in records)
        return {
            "user_id": user_id,
            "total_idle_seconds": total_seconds,
            "records": records,
        }
    except Exception as exc:
        print("GET MY IDLE ERROR:", repr(exc))
        raise HTTPException(
            status_code=500,
            detail="Could not load employee idle records."
        )


# --------------------------------------------------
# 16. LEAVE REQUESTS (REASON CHAT BOX & DATE)
# --------------------------------------------------

@app.post("/employee/leave-request")
def submit_leave_request(
    data: LeaveRequestData,
    user=Depends(current_user)
):
    if user["role"] != "employee":
        raise HTTPException(status_code=403, detail="Employee access required")

    user_id = str(user["user_id"])
    now_iso = datetime.now(timezone.utc).isoformat()
    emp_name = user.get("full_name") or user_id

    # 1. Try to insert directly into dedicated leave_requests table
    try:
        db.table("leave_requests").insert({
            "employee_id": user_id,
            "employee_name": emp_name,
            "leave_date": data.leave_date.strip(),
            "leave_type": data.leave_type.strip(),
            "reason": data.reason.strip(),
            "status": "Pending",
        }).execute()
        print(f"[LEAVE REQUEST]: Saved to leave_requests table for {user_id}")
    except Exception as tbl_err:
        print("[LEAVE REQUEST]: Dedicated leave_requests table not available yet, saving to employee_monitoring_logs:", tbl_err)

    # 2. Also save to employee_monitoring_logs as audit log
    record = {
        "employee_user_id": user_id,
        "event_name": "LEAVE_REQUEST",
        "event_timestamp": now_iso,
        "details": {
            "leave_date": data.leave_date.strip(),
            "leave_type": data.leave_type.strip(),
            "reason": data.reason.strip(),
            "status": "Pending",
            "applied_at": now_iso,
            "employee_name": emp_name,
        }
    }

    try:
        res = db.table("employee_monitoring_logs").insert(record).execute()
        return {
            "message": "Leave request submitted successfully",
            "data": res.data or []
        }
    except Exception as exc:
        print("LEAVE REQUEST SUBMIT ERROR:", repr(exc))
        raise HTTPException(
            status_code=500,
            detail="Failed to submit leave request to Supabase"
        )


@app.get("/employee/leave-requests")
def get_my_leave_requests(user=Depends(current_user)):
    user_id = str(user["user_id"])
    # 1. Try to read from dedicated leave_requests table
    try:
        tbl_res = (
            db.table("leave_requests")
            .select("employee_id,employee_name,leave_date,leave_type,reason,status,created_at")
            .eq("employee_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        if tbl_res.data:
            return {"leave_requests": tbl_res.data}
    except Exception:
        pass

    # 2. Fallback to employee_monitoring_logs
    try:
        res = (
            db.table("employee_monitoring_logs")
            .select("employee_user_id,event_timestamp,details,created_at")
            .eq("employee_user_id", user_id)
            .eq("event_name", "LEAVE_REQUEST")
            .order("event_timestamp", desc=True)
            .execute()
        )
        logs = res.data or []

        updates_res = (
            db.table("employee_monitoring_logs")
            .select("details,event_timestamp")
            .eq("employee_user_id", user_id)
            .eq("event_name", "LEAVE_STATUS_UPDATED")
            .order("event_timestamp", desc=True)
            .execute()
        )
        decision_map = {}
        for u in (updates_res.data or []):
            det = u.get("details") or {}
            key = f"{det.get('employee_id', user_id)}_{det.get('leave_date')}"
            if key not in decision_map:
                decision_map[key] = det.get("decision", "Pending")

        requests_list = []
        for row in logs:
            det = row.get("details") or {}
            key = f"{user_id}_{det.get('leave_date')}"
            status = decision_map.get(key, det.get("status", "Pending"))
            requests_list.append({
                "employee_id": user_id,
                "leave_date": det.get("leave_date", ""),
                "leave_type": det.get("leave_type", "Casual Leave"),
                "reason": det.get("reason", ""),
                "status": status,
                "applied_at": det.get("applied_at") or row.get("event_timestamp") or row.get("created_at")
            })

        return {"leave_requests": requests_list}
    except Exception as exc:
        print("GET MY LEAVE REQUESTS ERROR:", repr(exc))
        raise HTTPException(status_code=500, detail="Failed to load leave requests")


@app.get("/admin/leave-requests")
def get_all_leave_requests(admin=Depends(require_admin)):
    # 1. Try to read from dedicated leave_requests table
    try:
        tbl_res = (
            db.table("leave_requests")
            .select("employee_id,employee_name,leave_date,leave_type,reason,status,created_at")
            .order("created_at", desc=True)
            .limit(200)
            .execute()
        )
        if tbl_res.data:
            return {"leave_requests": tbl_res.data}
    except Exception:
        pass

    # 2. Fallback to employee_monitoring_logs
    try:
        res = (
            db.table("employee_monitoring_logs")
            .select("employee_user_id,event_timestamp,details,created_at")
            .eq("event_name", "LEAVE_REQUEST")
            .order("event_timestamp", desc=True)
            .limit(200)
            .execute()
        )
        logs = res.data or []

        updates_res = (
            db.table("employee_monitoring_logs")
            .select("details,event_timestamp")
            .eq("event_name", "LEAVE_STATUS_UPDATED")
            .order("event_timestamp", desc=True)
            .limit(200)
            .execute()
        )
        decision_map = {}
        for u in (updates_res.data or []):
            det = u.get("details") or {}
            key = f"{det.get('employee_id')}_{det.get('leave_date')}"
            if key not in decision_map:
                decision_map[key] = det.get("decision", "Pending")

        requests_list = []
        for row in logs:
            det = row.get("details") or {}
            emp_id = row.get("employee_user_id")
            key = f"{emp_id}_{det.get('leave_date')}"
            status = decision_map.get(key, det.get("status", "Pending"))
            requests_list.append({
                "employee_id": emp_id,
                "employee_name": det.get("employee_name", emp_id),
                "leave_date": det.get("leave_date", ""),
                "leave_type": det.get("leave_type", "Casual Leave"),
                "reason": det.get("reason", ""),
                "status": status,
                "applied_at": det.get("applied_at") or row.get("event_timestamp") or row.get("created_at")
            })

        return {"leave_requests": requests_list}
    except Exception as exc:
        print("ADMIN GET LEAVE REQUESTS ERROR:", repr(exc))
        raise HTTPException(status_code=500, detail="Failed to load all leave requests")


@app.post("/admin/leave-requests/decision")
def decide_leave_request(
    data: LeaveDecisionData,
    admin=Depends(require_admin)
):
    now_iso = datetime.now(timezone.utc).isoformat()

    # Try updating dedicated leave_requests table
    try:
        if data.employee_id and data.leave_date:
            db.table("leave_requests").update({"status": data.decision}).eq("employee_id", data.employee_id).eq("leave_date", data.leave_date).execute()
    except Exception:
        pass

    record = {
        "employee_user_id": admin["user_id"],
        "event_name": "LEAVE_STATUS_UPDATED",
        "event_timestamp": now_iso,
        "details": {
            "employee_id": data.employee_id,
            "leave_date": data.leave_date,
            "decision": data.decision,
            "admin_id": admin["user_id"],
            "comments": data.comments,
            "updated_at": now_iso,
        }
    }
    try:
        db.table("employee_monitoring_logs").insert(record).execute()
        return {"message": f"Leave request for {data.employee_id} ({data.leave_date}) marked as {data.decision}"}
    except Exception as exc:
        print("ADMIN LEAVE DECISION ERROR:", repr(exc))
        raise HTTPException(status_code=500, detail="Failed to update leave request status")


# --------------------------------------------------
# 17. MONITORING TAMPER & CANCELLATION ALERTS
# --------------------------------------------------

@app.post("/employee/cancel-attempt")
def report_cancel_attempt(
    data: CancelAttemptData,
    user=Depends(current_user)
):
    user_id = str(user["user_id"])
    now_iso = datetime.now(timezone.utc).isoformat()
    record = {
        "employee_user_id": user_id,
        "event_name": "MONITORING_CANCEL_ATTEMPT",
        "event_timestamp": now_iso,
        "details": {
            "reason": data.reason,
            "warning": "Unauthorized monitoring cancellation or close attempt intercepted",
            "action": "BLOCKED",
            "employee_name": user.get("full_name") or user_id,
            "extra": data.details or {},
        }
    }
    try:
        print(f"[TAMPER / CANCEL ALERT]: Employee '{user_id}' attempted to cancel monitoring: {data.reason}")
        res = db.table("employee_monitoring_logs").insert(record).execute()
        return {
            "status": "ALERT_RECORDED",
            "message": "Cancellation attempt logged in Supabase audit table",
            "data": res.data or []
        }
    except Exception as exc:
        print("CANCEL ATTEMPT LOG ERROR:", repr(exc))
        raise HTTPException(status_code=500, detail="Failed to log cancel attempt to Supabase")


@app.get("/admin/tamper-alerts")
def get_tamper_alerts(admin=Depends(require_admin)):
    try:
        res = (
            db.table("employee_monitoring_logs")
            .select("employee_user_id,event_name,event_timestamp,details,created_at")
            .eq("event_name", "MONITORING_CANCEL_ATTEMPT")
            .order("event_timestamp", desc=True)
            .limit(100)
            .execute()
        )
        return {"tamper_alerts": res.data or []}
    except Exception as exc:
        print("GET TAMPER ALERTS ERROR:", repr(exc))
        raise HTTPException(status_code=500, detail="Failed to load tamper alerts")


# --------------------------------------------------
# 18. ATTENDANCE PUNCH IN & OUT
# --------------------------------------------------

@app.post("/employee/attendance/check-in")
def attendance_check_in(user=Depends(current_user)):
    user_id = str(user["user_id"])
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        res = (
            db.table("employee_attendance")
            .select("attendance_in,attendance_out")
            .eq("username", user_id)
            .is_("attendance_out", "null")
            .order("attendance_in", desc=True)
            .limit(1)
            .execute()
        )
        if res.data:
            return {"message": "Already checked in", "record": res.data[0]}

        insert_res = db.table("employee_attendance").insert({
            "username": user_id,
            "attendance_in": now_iso
        }).execute()
        return {"message": "Attendance punched IN successfully", "record": insert_res.data or []}
    except Exception as exc:
        print("ATTENDANCE CHECK-IN ERROR:", repr(exc))
        raise HTTPException(status_code=500, detail="Check-in failed")


@app.post("/employee/attendance/check-out")
def attendance_check_out(user=Depends(current_user)):
    user_id = str(user["user_id"])
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        res = (
            db.table("employee_attendance")
            .select("attendance_in,attendance_out")
            .eq("username", user_id)
            .is_("attendance_out", "null")
            .order("attendance_in", desc=True)
            .limit(1)
            .execute()
        )
        if res.data:
            att_in = res.data[0]["attendance_in"]
            db.table("employee_attendance").update({
                "attendance_out": now_iso
            }).eq("username", user_id).eq("attendance_in", att_in).execute()
            return {"message": "Attendance punched OUT successfully"}
        else:
            db.table("employee_attendance").insert({
                "username": user_id,
                "attendance_in": now_iso,
                "attendance_out": now_iso
            }).execute()
            return {"message": "Attendance check-out recorded"}
    except Exception as exc:
        print("ATTENDANCE CHECK-OUT ERROR:", repr(exc))
        raise HTTPException(status_code=500, detail="Check-out failed")
