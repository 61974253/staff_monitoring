
import json
import time
import os
import atexit
import subprocess
import sys
import threading

from pathlib import Path
from datetime import datetime
from pynput import mouse, keyboard


# ---------------- CONFIGURATION ----------------

IDLE_THRESHOLD = 30  # Idle threshold in seconds

BASE_DIR = Path(__file__).resolve().parent

LOG_FILE = BASE_DIR / "events.jsonl"
BLACK_SCREEN_FILE = BASE_DIR / "blackscreen.py"

last_activity = time.monotonic()
last_check = time.monotonic()

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

    with open(LOG_FILE, "a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")
        file.flush()
        os.fsync(file.fileno())

    print(record)


# ---------------- ACTIVITY DETECTION ----------------

def record_activity():
    global last_activity
    last_activity = time.monotonic()


def on_mouse_move(x, y):
    record_activity()


def on_mouse_click(x, y, button, pressed):
    if pressed:
        record_activity()


def on_key_press(key):
    # Never record the actual keys typed.
    record_activity()


# ---------------- BLACK SCREEN ----------------

def is_black_screen_running():
    global black_screen_process

    with black_screen_lock:
        if black_screen_process is not None:
            if black_screen_process.poll() is None:
                return True

            black_screen_process = None

    return False


def open_black_screen():
    global black_screen_process

    if not BLACK_SCREEN_FILE.exists():
        log_event(
            "BLACK_SCREEN_ERROR",
            {"message": "black_screen.py file not found"}
        )
        return

    with black_screen_lock:
        if black_screen_process is not None:
            if black_screen_process.poll() is None:
                return

        black_screen_process = subprocess.Popen(
            [sys.executable, str(BLACK_SCREEN_FILE)],
            cwd=str(BASE_DIR)
        )

    log_event("BLACK_SCREEN_OPENED")


# ---------------- SUMMARY ----------------

def save_summary():
    log_event(
        "SESSION_SUMMARY",
        {
            "active_input_seconds": round(active_seconds),
            "idle_seconds": round(idle_seconds),
            "note": (
                "Input-based activity estimate; "
                "not proof of productive work."
            )
        }
    )


# ---------------- MONITORING ----------------

def main():
    global last_check
    global current_status
    global active_seconds
    global idle_seconds
    global running

    mouse_listener = mouse.Listener(
        on_move=on_mouse_move,
        on_click=on_mouse_click
    )

    keyboard_listener = keyboard.Listener(
        on_press=on_key_press
    )

    mouse_listener.start()
    keyboard_listener.start()

    log_event(
        "MONITORING_STARTED",
        {"idle_threshold_seconds": IDLE_THRESHOLD}
    )

    atexit.register(save_summary)

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
                current_status = new_status

                log_event(
                    f"STATUS_{new_status}",
                    {"no_input_seconds": round(no_input)}
                )

            # Open the screen once when idle begins.
            if new_status == "IDLE":
                if not is_black_screen_running():
                    open_black_screen()

            time.sleep(1)

    except KeyboardInterrupt:
        log_event("MONITORING_STOPPED")

    finally:
        running = False

        mouse_listener.stop()
        keyboard_listener.stop()

        log_event("MONITORING_STOPPED")


if __name__ == "__main__":
    main()

