
import json
import time
import os
import subprocess
import sys
import threading
import signal
import ctypes

from pathlib import Path
from datetime import datetime, timedelta
from pynput import mouse, keyboard
import requests


<<<<<<< HEAD
# Backend API endpoint
API_URL = "http://127.0.0.1:8002/employee/monitoring-events"

# Read the employee login token from the environment
ACCESS_TOKEN = os.environ.get("EMPLOYEE_ACCESS_TOKEN", "")


=======
>>>>>>> 5a595d8 (feat: enhance admin web dashboard, employee monitoring, and remove id column dependencies)
# ---------------- CONFIGURATION ----------------

API_URL = "http://127.0.0.1:8000/employee/monitoring-events"
CANCEL_API_URL = "http://127.0.0.1:8000/employee/cancel-attempt"
ACCESS_TOKEN = os.environ.get("EMPLOYEE_ACCESS_TOKEN", "")
USER_ID = os.environ.get("EMPLOYEE_USER_ID", "employee")

IDLE_THRESHOLD = 60  # Seconds without mouse/keyboard input

BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "events.jsonl"
BLACK_SCREEN_FILE = BASE_DIR / "blackscreen.py"
SESSION_STATUS_FILE = BASE_DIR / "live_session.json"
AUTH_SIGNOUT_FLAG = BASE_DIR / "authorized_signout.flag"

# Clean up any leftover auth signout flag from earlier sessions
if AUTH_SIGNOUT_FLAG.exists():
    try:
        AUTH_SIGNOUT_FLAG.unlink()
    except OSError:
        pass

session_start_time = datetime.now().astimezone()
last_activity = time.monotonic()
last_activity_at = datetime.now().astimezone()
last_check = time.monotonic()
idle_started_at = None

active_seconds = 0.0
idle_seconds = 0.0

current_status = "ACTIVE"
running = True
shutdown_started = False
is_authorized_exit = False

idle_started_at = None
idle_session_seconds = 0.0

black_screen_process = None
black_screen_lock = threading.Lock()
activity_lock = threading.Lock()
shutdown_lock = threading.Lock()


def write_live_session(status, act_sec, idl_sec, is_black_screen):
    """Write live metrics so employee dashboard displays real-time live data."""
    try:
        data = {
            "user_id": USER_ID,
            "status": "BREAK" if is_black_screen else status,
            "active_seconds": round(act_sec, 1),
            "idle_seconds": round(idl_sec, 1),
            "total_seconds": round(act_sec + idl_sec, 1),
            "updated_at": time.time(),
            "session_start": session_start_time.isoformat(),
            "black_screen_active": is_black_screen,
        }
        temp_file = BASE_DIR / "live_session.json.tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f)
        temp_file.replace(SESSION_STATUS_FILE)
    except Exception:
        pass


def report_cancel_violation(reason="Monitoring agent terminated unexpectedly or cancelled"):
    """Report unauthorized cancellation attempt to Supabase and show alert."""
    print(f"\n[TAMPER / CANCEL ALERT]: Unauthorized monitoring cancellation attempt detected: {reason}")
    log_event("MONITORING_CANCEL_ATTEMPT", {
        "reason": reason,
        "active_seconds": round(active_seconds),
        "idle_seconds": round(idle_seconds),
        "user_id": USER_ID
    })

    if ACCESS_TOKEN:
        try:
            requests.post(
                CANCEL_API_URL,
                json={
                    "reason": reason,
                    "details": {
                        "active_seconds": round(active_seconds),
                        "idle_seconds": round(idle_seconds),
                        "user_id": USER_ID
                    }
                },
                headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
                timeout=5
            )
        except Exception as e:
            print("FAILED TO SEND CANCEL ALERT TO BACKEND:", e)

    # Display Windows alert dialog to notify employee
    try:
        msg = (
            "CORPORATE MONITORING POLICY WARNING:\n\n"
            "Workstation monitoring cannot be cancelled or closed during working hours.\n"
            "This cancellation incident has been recorded in the Supabase audit database.\n\n"
            "Official sign-out through the portal is required to end shift."
        )
        ctypes.windll.user32.MessageBoxW(0, msg, "TCS Workstation Monitor - Tamper Alert", 0x10 | 0x40000)
    except Exception:
        pass


# ---------------- EVENT LOGGER ----------------

def log_event(event_name, details=None):
    record = {
        "event": event_name,
        "timestamp": datetime.now().astimezone().isoformat(),
        "details": details or {}
    }

    # Save locally first
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as file:
            file.write(json.dumps(record) + "\n")
            file.flush()
            os.fsync(file.fileno())
    except OSError as error:
        print("LOCAL LOG ERROR:", error)

    print(record)

    # Upload using existing authenticated backend endpoint
    if not ACCESS_TOKEN:
        print("UPLOAD FAILED: Employee login token is missing.")
        return False

    try:
        response = requests.post(
            API_URL,
            json=record,
            headers={
                "Authorization": f"Bearer {ACCESS_TOKEN}"
            },
            timeout=10
        )

        if response.ok:
<<<<<<< HEAD
            print("SUPABASE UPLOAD: SUCCESS")
            return True
=======
            print("BACKEND UPLOAD: SUCCESS")
>>>>>>> 5a595d8 (feat: enhance admin web dashboard, employee monitoring, and remove id column dependencies)
        else:
            print(
                "BACKEND UPLOAD: FAILED",
                response.status_code,
                response.text
            )
            return False

    except requests.RequestException as error:
        print("UPLOAD CONNECTION ERROR:", error)
        return False


# ---------------- ACTIVITY DETECTION ----------------

def record_activity():
<<<<<<< HEAD
    global last_activity, last_activity_at
    last_activity = time.monotonic()
    last_activity_at = datetime.now().astimezone()
=======
    global last_activity

    with activity_lock:
        last_activity = time.monotonic()
>>>>>>> 5a595d8 (feat: enhance admin web dashboard, employee monitoring, and remove id column dependencies)


def on_mouse_move(x, y):
    record_activity()


def on_mouse_click(x, y, button, pressed):
    if pressed:
        record_activity()


def on_mouse_scroll(x, y, dx, dy):
    record_activity()


def on_key_press(key):
    # Detect activity only. Never save actual typed keys.
    record_activity()


# ---------------- BLACK SCREEN ----------------

def open_black_screen():
    global black_screen_process

    if not BLACK_SCREEN_FILE.exists():
        log_event(
            "BLACK_SCREEN_ERROR",
<<<<<<< HEAD
            {"message": f"Black screen file not found: {BLACK_SCREEN_FILE}"}
=======
            {"message": "blackscreen.py file not found"}
>>>>>>> 5a595d8 (feat: enhance admin web dashboard, employee monitoring, and remove id column dependencies)
        )
        return

    with black_screen_lock:
        if (
            black_screen_process is not None
            and black_screen_process.poll() is None
        ):
            return

        try:
<<<<<<< HEAD
            black_screen_process = subprocess.Popen(
                [sys.executable, str(BLACK_SCREEN_FILE)],
                cwd=str(BASE_DIR),
                stdin=subprocess.PIPE,
                text=True
=======
            agent_env = os.environ.copy()
            if ACCESS_TOKEN:
                agent_env["EMPLOYEE_ACCESS_TOKEN"] = ACCESS_TOKEN
            black_screen_process = subprocess.Popen(
                [sys.executable, str(BLACK_SCREEN_FILE)],
                cwd=str(BASE_DIR),
                env=agent_env
>>>>>>> 5a595d8 (feat: enhance admin web dashboard, employee monitoring, and remove id column dependencies)
            )
        except OSError as error:
            log_event(
                "BLACK_SCREEN_ERROR",
<<<<<<< HEAD
                {"message": f"Could not launch black screen: {error}"}
=======
                {"message": str(error)}
>>>>>>> 5a595d8 (feat: enhance admin web dashboard, employee monitoring, and remove id column dependencies)
            )
            return

    log_event("BLACK_SCREEN_OPENED")


# ---------------- SESSION SUMMARY ----------------

def save_summary():
    if not log_event(
        "SESSION_SUMMARY",
        {
            "active_input_seconds": round(active_seconds),
            "idle_seconds": round(idle_seconds),
            "note": (
                "Input-based activity estimate; "
                "not proof of productive work."
            )
        }
    ):
        raise RuntimeError("Could not save the final activity summary")


def save_idle_session(end_time):
    global idle_started_at

    if idle_started_at is None:
        return

    idle_seconds_for_session = max(
        0,
        round((end_time - idle_started_at).total_seconds())
    )
    log_event(
        "IDLE_SESSION",
        {
            "idle_start": idle_started_at.isoformat(),
            "idle_end": end_time.isoformat(),
            "idle_seconds": idle_seconds_for_session,
        }
    )
    idle_started_at = None


def stop_black_screen():
    global black_screen_process

    process = black_screen_process
    if process is None:
        return

    if process.poll() is None:
        if process.stdin is not None:
            try:
                process.stdin.write("logout\n")
                process.stdin.flush()
            except (BrokenPipeError, OSError):
                pass

        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    if process.stdin is not None:
        process.stdin.close()
    black_screen_process = None


# ---------------- IDLE TRANSITIONS ----------------

def start_idle(no_input):
    global current_status
    global idle_started_at
    global idle_session_seconds

    if current_status == "IDLE":
        return

    current_status = "IDLE"
    idle_started_at = datetime.now().astimezone()
    idle_session_seconds = 0.0

    log_event(
        "IDLE_STARTED",
        {
            "idle_start": idle_started_at.isoformat(),
            "idle_threshold_seconds": IDLE_THRESHOLD,
            "no_input_seconds": round(no_input)
        }
    )

    log_event(
        "STATUS_IDLE",
        {"no_input_seconds": round(no_input)}
    )

    open_black_screen()


def stop_idle():
    global current_status
    global idle_started_at
    global idle_session_seconds

    if current_status != "IDLE":
        return

    idle_end = datetime.now().astimezone()

    if idle_started_at is not None:
        # Measure actual elapsed time since idle was detected.
        duration = max(
            0,
            int((idle_end - idle_started_at).total_seconds())
        )
        idle_start_text = idle_started_at.isoformat()
    else:
        duration = int(idle_session_seconds)
        idle_start_text = None

    log_event(
        "IDLE_ENDED",
        {
            "idle_start": idle_start_text,
            "idle_end": idle_end.isoformat(),
            "duration_seconds": duration
        }
    )

    current_status = "ACTIVE"
    idle_started_at = None
    idle_session_seconds = 0.0

    log_event("STATUS_ACTIVE", {"idle_duration_seconds": duration})


# ---------------- MONITORING ----------------

def main():
    global last_check
    global active_seconds
    global idle_seconds
    global running
<<<<<<< HEAD
    global idle_started_at

    def listen_for_logout():
        global running
        if sys.stdin is None:
            return
        for command in sys.stdin:
            if command.strip().lower() == "logout":
                running = False
                return
=======
    
    idle_session_seconds = 0.0
>>>>>>> 5a595d8 (feat: enhance admin web dashboard, employee monitoring, and remove id column dependencies)

    mouse_listener = mouse.Listener(
        on_move=on_mouse_move,
        on_click=on_mouse_click,
        on_scroll=on_mouse_scroll
    )

    keyboard_listener = keyboard.Listener(
        on_press=on_key_press
    )

    mouse_listener.start()
    keyboard_listener.start()
    threading.Thread(target=listen_for_logout, daemon=True).start()


    log_event(
        "MONITORING_STARTED",
        {"idle_threshold_seconds": IDLE_THRESHOLD}
    )

    try:
        while running:
            now = time.monotonic()
            elapsed = now - last_check
            last_check = now

            with activity_lock:
                no_input = now - last_activity

            black_screen_active = is_black_screen_running()

            if no_input >= IDLE_THRESHOLD or black_screen_active:
                new_status = "IDLE"
            else:
                new_status = "ACTIVE"

            if new_status == "IDLE":
                idle_seconds += elapsed

<<<<<<< HEAD
            if new_status != current_status:
                previous_status = current_status
                current_status = new_status
=======
                if current_status != "IDLE":
                    start_idle(no_input)
>>>>>>> 5a595d8 (feat: enhance admin web dashboard, employee monitoring, and remove id column dependencies)

            else:
                active_seconds += elapsed

<<<<<<< HEAD
                if new_status == "IDLE":
                    idle_started_at = min(
                        last_activity_at + timedelta(seconds=IDLE_THRESHOLD),
                        datetime.now().astimezone()
                    )
                    open_black_screen()
                elif previous_status == "IDLE":
                    save_idle_session(datetime.now().astimezone())
=======
                if current_status == "IDLE":
                    stop_idle()
>>>>>>> 5a595d8 (feat: enhance admin web dashboard, employee monitoring, and remove id column dependencies)

            time.sleep(1)

            # Sync live metrics to session file for employee dashboard
            write_live_session(
                current_status,
                active_seconds,
                idle_seconds,
                black_screen_active
            )

    except KeyboardInterrupt:
<<<<<<< HEAD
        print("\nMonitoring stopped by user.")
=======
        print("Monitoring interrupted by user/system.")
        if not (AUTH_SIGNOUT_FLAG.exists() or is_authorized_exit):
            report_cancel_violation("Process interrupted via KeyboardInterrupt / Console Cancel")
>>>>>>> 5a595d8 (feat: enhance admin web dashboard, employee monitoring, and remove id column dependencies)

    finally:
        running = False

        mouse_listener.stop()
        keyboard_listener.stop()

<<<<<<< HEAD
        stopped_at = datetime.now().astimezone()
        final_elapsed = max(0, time.monotonic() - last_check)
        if current_status == "IDLE":
            idle_seconds += final_elapsed
        else:
            active_seconds += final_elapsed
        last_check = time.monotonic()

        stop_black_screen()

        if current_status == "IDLE":
            save_idle_session(stopped_at)

        log_event("MONITORING_STOPPED")
        save_summary()
=======
        # Close an open idle period when monitoring exits.
        stop_idle()

        # Check if exit was legitimately authorized through dashboard sign-out
        if not (AUTH_SIGNOUT_FLAG.exists() or is_authorized_exit):
            report_cancel_violation("Workstation monitoring stopped without authorized sign-out")
        else:
            print("Authorized sign-out completed.")

        log_event("MONITORING_STOPPED")
        save_summary()

        # Clean up session file on exit
        try:
            if SESSION_STATUS_FILE.exists():
                SESSION_STATUS_FILE.unlink()
            if AUTH_SIGNOUT_FLAG.exists():
                AUTH_SIGNOUT_FLAG.unlink()
        except OSError:
            pass


def handle_signal(signum, frame):
    global running
    print(f"Signal received: {signum}")
    if not (AUTH_SIGNOUT_FLAG.exists() or is_authorized_exit):
        report_cancel_violation(f"Termination signal {signum} intercepted")
    running = False


try:
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
except Exception:
    pass


def shutdown():
    global running
    global shutdown_started

    with shutdown_lock:
        if shutdown_started:
            return
        shutdown_started = True

    running = False


atexit.register(shutdown)
>>>>>>> 5a595d8 (feat: enhance admin web dashboard, employee monitoring, and remove id column dependencies)


if __name__ == "__main__":
    main()
