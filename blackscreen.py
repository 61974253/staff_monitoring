
import tkinter as tk
import json
import os

from pathlib import Path
from datetime import datetime


# ---------------- CONFIGURATION ----------------

BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "events.jsonl"

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

root.mainloop()

