
import json
import time
import os
import subprocess
import sys
import threading

from pathlib import Path
from datetime import datetime, timedelta
from pynput import mouse, keyboard
import requests


# Backend API endpoint
API_URL = "http://127.0.0.1:8002/employee/monitoring-events"

# Read the employee login token from the environment
ACCESS_TOKEN = os.environ.get("EMPLOYEE_ACCESS_TOKEN", "")


# ---------------- CONFIGURATION ----------------

IDLE_THRESHOLD = 30  # Idle threshold in seconds

BASE_DIR = Path(__file__).resolve().parent

LOG_FILE = BASE_DIR / "events.jsonl"
BLACK_SCREEN_FILE = BASE_DIR / "blackscreen.py"

last_activity = time.monotonic()
last_activity_at = datetime.now().astimezone()
last_check = time.monotonic()
idle_started_at = None

active_seconds = 0.0
idle_seconds = 0.0

current_status = "ACTIVE"
running = True

black_screen_process = None
black_screen_lock = threading.Lock()


# ---------------- EVENT LOGGER ----------------


def log_event(event_name, details=None):
    record = {
        "event": event_name,
        "timestamp": datetime.now().astimezone().isoformat(),
        "details": details or {}
    }

    # Keep a local copy of the event
    with open(LOG_FILE, "a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")
        file.flush()
        os.fsync(file.fileno())

    # Print the event in the terminal
    print(record)

    # Upload the event to the backend
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
            print("SUPABASE UPLOAD: SUCCESS")
            return True
        else:
            print(
                "SUPABASE UPLOAD: FAILED",
                response.status_code,
                response.text
            )
            return False

    except requests.RequestException as error:
        print("UPLOAD CONNECTION ERROR:", error)
        return False



# ---------------- ACTIVITY DETECTION ----------------

def record_activity():
    global last_activity, last_activity_at
    last_activity = time.monotonic()
    last_activity_at = datetime.now().astimezone()


def on_mouse_move(x, y):
    record_activity()


def on_mouse_click(x, y, button, pressed):
    if pressed:
        record_activity()


def on_key_press(key):
    # Never record the actual keys typed.
    record_activity()


# ---------------- BLACK SCREEN ----------------

def open_black_screen():
    global black_screen_process

    if not BLACK_SCREEN_FILE.exists():
        log_event(
            "BLACK_SCREEN_ERROR",
            {"message": f"Black screen file not found: {BLACK_SCREEN_FILE}"}
        )
        return

    with black_screen_lock:
        if black_screen_process is not None:
            if black_screen_process.poll() is None:
                return

        try:
            black_screen_process = subprocess.Popen(
                [sys.executable, str(BLACK_SCREEN_FILE)],
                cwd=str(BASE_DIR),
                stdin=subprocess.PIPE,
                text=True
            )
        except OSError as error:
            log_event(
                "BLACK_SCREEN_ERROR",
                {"message": f"Could not launch black screen: {error}"}
            )
            return

    log_event("BLACK_SCREEN_OPENED")


# ---------------- SUMMARY ----------------

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


# ---------------- MONITORING ----------------

def main():
    global last_check
    global current_status
    global active_seconds
    global idle_seconds
    global running
    global idle_started_at

    def listen_for_logout():
        global running
        if sys.stdin is None:
            return
        for command in sys.stdin:
            if command.strip().lower() == "logout":
                running = False
                return

    mouse_listener = mouse.Listener(
        on_move=on_mouse_move,
        on_click=on_mouse_click
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

            no_input = now - last_activity

            if no_input >= IDLE_THRESHOLD:
                new_status = "IDLE"
            else:
                new_status = "ACTIVE"

            if new_status == "ACTIVE":
                active_seconds += elapsed
            else:
                idle_seconds += elapsed

            if new_status != current_status:
                previous_status = current_status
                current_status = new_status

                log_event(
                    f"STATUS_{new_status}",
                    {"no_input_seconds": round(no_input)}
                )

                if new_status == "IDLE":
                    idle_started_at = min(
                        last_activity_at + timedelta(seconds=IDLE_THRESHOLD),
                        datetime.now().astimezone()
                    )
                    open_black_screen()
                elif previous_status == "IDLE":
                    save_idle_session(datetime.now().astimezone())

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")

    finally:
        running = False

        mouse_listener.stop()
        keyboard_listener.stop()

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


if __name__ == "__main__":
    main()
