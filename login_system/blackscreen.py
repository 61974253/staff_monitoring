
import tkinter as tk
import json
import os
import requests
import sys
import threading

from pathlib import Path
from datetime import datetime


# ---------------- CONFIGURATION ----------------

BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "events.jsonl"
API_URL = "http://127.0.0.1:8002/employee/monitoring-events"
BREAK_SESSION_API_URL = "http://127.0.0.1:8002/employee/employee-break-sessions"
ACCESS_TOKEN = os.environ.get("EMPLOYEE_ACCESS_TOKEN", "")

start_time = datetime.now()
timer_running = True


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

    if not ACCESS_TOKEN:
        print("UPLOAD FAILED: Employee login token is missing.")
        return

    
    if event_name == "BREAK_SESSION":
       upload_url = BREAK_SESSION_API_URL
       upload_record = {
        "break_start": (details or {}).get("start_time"),
        "break_end": (details or {}).get("end_time"),
        "break_reason": (details or {}).get("reason"),
        "break_type": (details or {}).get("reason") or "personal",
    }

    else:
        upload_url = API_URL
        upload_record = record

    try:
        response = requests.post(
            upload_url,
            json=upload_record,
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
            timeout=10
        )

        if response.ok:
            print(f"SUPABASE UPLOAD: {event_name} saved")
        else:
            print(
                f"SUPABASE UPLOAD FAILED: {event_name}",
                response.status_code,
                response.text
            )
    except requests.RequestException as error:
        print(f"UPLOAD CONNECTION ERROR ({event_name}):", error)


# ---------------- TIMER ----------------

def update_timer():
    if not timer_running:
        return

    elapsed = int((datetime.now() - start_time).total_seconds())

    hours = elapsed // 3600
    minutes = (elapsed % 3600) // 60
    seconds = elapsed % 60

    timer_label.config(
        text=f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    )

    root.after(1000, update_timer)


# ---------------- RESUME ----------------

def resume_work():
    global timer_running

    reason = reason_var.get().strip()
    notes = notes_entry.get().strip()

    if not reason:
        message_label.config(
            text="Please select a reason.",
            fg="#ff7777"
        )
        return

    timer_running = False

    elapsed = int((datetime.now() - start_time).total_seconds())

    log_event(
        "BREAK_SESSION",
        {
            "start_time": start_time.astimezone().isoformat(),
            "end_time": datetime.now().astimezone().isoformat(),
            "duration_seconds": elapsed,
            "reason": reason,
            "notes": notes
        }
    )

    root.destroy()


def close_for_logout():
    global timer_running
    timer_running = False
    root.destroy()


def listen_for_logout():
    if sys.stdin is None:
        return

    for command in sys.stdin:
        if command.strip().lower() == "logout":
            root.after(0, close_for_logout)
            return


# ---------------- WINDOW ----------------

root = tk.Tk()

root.title("Idle / Break Monitor")
root.configure(bg="black")

# Black window; do not force a Windows system lock.
root.attributes("-fullscreen", True)

root.bind("<Escape>", lambda event: resume_work())

# Main content
container = tk.Frame(root, bg="black")
container.pack(expand=True)

title_label = tk.Label(
    container,
    text="WORKSTATION PAUSED",
    font=("Arial", 24, "bold"),
    fg="white",
    bg="black"
)
title_label.pack(pady=20)

subtitle_label = tk.Label(
    container,
    text="Idle / Break Session",
    font=("Arial", 14),
    fg="#aaaaaa",
    bg="black"
)
subtitle_label.pack(pady=5)

timer_label = tk.Label(
    container,
    text="00:00:00",
    font=("Consolas", 42, "bold"),
    fg="white",
    bg="black"
)
timer_label.pack(pady=20)

reason_label = tk.Label(
    container,
    text="Select your reason",
    font=("Arial", 12),
    fg="white",
    bg="black"
)
reason_label.pack(pady=8)

reason_var = tk.StringVar(value="")

reason_menu = tk.OptionMenu(
    container,
    reason_var,
    "Short break",
    "Lunch / tea break",
    "Work-related discussion",
    "System issue",
    "Other"
)

reason_menu.config(
    font=("Arial", 12),
    bg="#222222",
    fg="white",
    activebackground="#444444",
    activeforeground="white",
    width=25
)

reason_menu["menu"].config(
    bg="#222222",
    fg="white"
)

reason_menu.pack(pady=10)

notes_entry = tk.Entry(
    container,
    font=("Arial", 12),
    width=35
)
notes_entry.pack(pady=10)

notes_entry.insert(0, "")

resume_button = tk.Button(
    container,
    text="SUBMIT REASON & RESUME",
    font=("Arial", 12, "bold"),
    bg="white",
    fg="black",
    activebackground="#dddddd",
    command=resume_work,
    padx=20,
    pady=10
)
resume_button.pack(pady=20)

message_label = tk.Label(
    container,
    text="",
    font=("Arial", 11),
    fg="white",
    bg="black"
)
message_label.pack(pady=5)

log_event(
    "BLACK_SCREEN_STARTED",
    {"start_time": start_time.astimezone().isoformat()}
)

update_timer()
threading.Thread(target=listen_for_logout, daemon=True).start()

root.mainloop()
