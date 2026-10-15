import json
import os
import sys
import time
from datetime import datetime, date, timedelta
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
import requests

API_BASE_URL = "http://127.0.0.1:8000"
BASE_DIR = Path(__file__).resolve().parent
SESSION_STATUS_FILE = BASE_DIR / "live_session.json"
AUTH_SIGNOUT_FLAG = BASE_DIR / "authorized_signout.flag"

# Standard workday shift: 8 hours (28,800 seconds)
SHIFT_TARGET_SECONDS = 8 * 3600


class EmployeeDashboard:
    def __init__(self, root, access_token, user_id, full_name, agent_process=None):
        self.root = root
        self.access_token = access_token
        self.user_id = str(user_id)
        self.full_name = full_name or user_id
        self.agent_process = agent_process

        # Session tracking state
        self.session_start = datetime.now()
        self.login_time_str = self.session_start.strftime("%I:%M:%S %p")
        self.logout_time_str = "--:--:--"

        self.active_seconds = 0.0
        self.idle_seconds = 0.0
        self.current_status = "ACTIVE"
        self.is_signed_out = False

        # Compact small box window
        self.root.title(f"Staff Monitor - {self.user_id}")
        self.root.geometry("460x610")
        self.root.resizable(False, False)
        self.root.configure(bg="#f8fafc")

        # Intercept window close (Alt+F4 or [X] button) to block cancellation!
        self.root.protocol("WM_DELETE_WINDOW", self.on_attempt_cancel_close)

        # Build compact UI
        self.build_compact_ui()

        # Start live ticker loop (every 1 second)
        self.update_live_tick()

    def build_compact_ui(self):
        # 1. Header (User Info + Status Badge)
        header = tk.Frame(self.root, bg="#0f172a", padx=16, pady=12)
        header.pack(fill="x")

        title_lbl = tk.Label(
            header,
            text=f"{self.full_name}  ({self.user_id})",
            font=("Segoe UI", 12, "bold"),
            fg="#f8fafc",
            bg="#0f172a"
        )
        title_lbl.pack(side="left")

        self.status_badge = tk.Label(
            header,
            text="● ACTIVE",
            font=("Segoe UI", 9, "bold"),
            fg="#4ade80",
            bg="#0f172a"
        )
        self.status_badge.pack(side="right")

        # Main content container
        content = tk.Frame(self.root, bg="#f8fafc", padx=18, pady=12)
        content.pack(fill="both", expand=True)

        # 2. Time Tracker Card (White Box)
        tracker_card = tk.LabelFrame(
            content,
            text=" ⏱️ Work Time & Session Tracker ",
            font=("Segoe UI", 9, "bold"),
            bg="#ffffff",
            fg="#1e293b",
            padx=14,
            pady=10,
            relief="solid",
            bd=1
        )
        tracker_card.pack(fill="x", pady=(0, 10))

        # Grid of times
        # Row 0: Login Time & Logout Time
        tk.Label(tracker_card, text="Login Time:", font=("Segoe UI", 9, "bold"), fg="#64748b", bg="#ffffff").grid(row=0, column=0, sticky="w", pady=4)
        self.login_lbl = tk.Label(tracker_card, text=self.login_time_str, font=("Consolas", 10, "bold"), fg="#2563eb", bg="#ffffff")
        self.login_lbl.grid(row=0, column=1, sticky="w", padx=(10, 20), pady=4)

        tk.Label(tracker_card, text="Logout Time:", font=("Segoe UI", 9, "bold"), fg="#64748b", bg="#ffffff").grid(row=0, column=2, sticky="w", pady=4)
        self.logout_lbl = tk.Label(tracker_card, text=self.logout_time_str, font=("Consolas", 10, "bold"), fg="#94a3b8", bg="#ffffff")
        self.logout_lbl.grid(row=0, column=3, sticky="w", padx=10, pady=4)

        # Separator line inside card
        sep = tk.Frame(tracker_card, height=1, bg="#e2e8f0")
        sep.grid(row=1, column=0, columnspan=4, sticky="ew", pady=6)

        # Row 2: Live Work Time
        tk.Label(tracker_card, text="Work Time:", font=("Segoe UI", 10, "bold"), fg="#0f172a", bg="#ffffff").grid(row=2, column=0, sticky="w", pady=4)
        self.work_time_lbl = tk.Label(tracker_card, text="00:00:00", font=("Consolas", 13, "bold"), fg="#16a34a", bg="#ffffff")
        self.work_time_lbl.grid(row=2, column=1, sticky="w", padx=(10, 20), pady=4)

        # Row 2: Live Idle Time
        tk.Label(tracker_card, text="Idle Time:", font=("Segoe UI", 10, "bold"), fg="#0f172a", bg="#ffffff").grid(row=2, column=2, sticky="w", pady=4)
        self.idle_time_lbl = tk.Label(tracker_card, text="00:00:00", font=("Consolas", 13, "bold"), fg="#d97706", bg="#ffffff")
        self.idle_time_lbl.grid(row=2, column=3, sticky="w", padx=10, pady=4)

        # Row 3: Over Work Time (Overtime)
        tk.Label(tracker_card, text="Over Work Time:", font=("Segoe UI", 10, "bold"), fg="#0f172a", bg="#ffffff").grid(row=3, column=0, sticky="w", pady=4)
        self.over_time_lbl = tk.Label(tracker_card, text="00:00:00", font=("Consolas", 13, "bold"), fg="#7c3aed", bg="#ffffff")
        self.over_time_lbl.grid(row=3, column=1, sticky="w", padx=(10, 20), pady=4)

        self.over_status_lbl = tk.Label(tracker_card, text="(Target: 8.0h shift)", font=("Segoe UI", 8), fg="#64748b", bg="#ffffff")
        self.over_status_lbl.grid(row=3, column=2, columnspan=2, sticky="w", padx=10, pady=4)

        # 3. Leave Request Card (With Reason Chat Box & Leave Date)
        leave_card = tk.LabelFrame(
            content,
            text=" 📝 Leave Request ",
            font=("Segoe UI", 9, "bold"),
            bg="#ffffff",
            fg="#1e293b",
            padx=14,
            pady=10,
            relief="solid",
            bd=1
        )
        leave_card.pack(fill="both", expand=True, pady=(0, 10))

        # Date input row
        date_row = tk.Frame(leave_card, bg="#ffffff")
        date_row.pack(fill="x", pady=(0, 6))

        tk.Label(date_row, text="Leave Date:", font=("Segoe UI", 9, "bold"), bg="#ffffff", fg="#334155").pack(side="left")

        tomorrow_str = (date.today() + timedelta(days=1)).isoformat()
        self.leave_date_entry = tk.Entry(date_row, font=("Segoe UI", 9), width=12, bg="#f1f5f9", bd=1, relief="solid")
        self.leave_date_entry.insert(0, tomorrow_str)
        self.leave_date_entry.pack(side="left", padx=8, ipady=2)

        today_btn = tk.Button(
            date_row,
            text="Today",
            font=("Segoe UI", 8),
            bg="#e2e8f0",
            relief="flat",
            command=lambda: self.set_leave_date(date.today().isoformat())
        )
        today_btn.pack(side="left", padx=2)

        tmrw_btn = tk.Button(
            date_row,
            text="Tomorrow",
            font=("Segoe UI", 8),
            bg="#e2e8f0",
            relief="flat",
            command=lambda: self.set_leave_date((date.today() + timedelta(days=1)).isoformat())
        )
        tmrw_btn.pack(side="left", padx=2)

        # Reason Chat Box (Text box for explaining reason)
        tk.Label(
            leave_card,
            text="💬 Reason Chat Box:",
            font=("Segoe UI", 9, "bold"),
            bg="#ffffff",
            fg="#1d4ed8"
        ).pack(anchor="w", pady=(2, 2))

        self.reason_text = tk.Text(
            leave_card,
            font=("Segoe UI", 9),
            height=3,
            bg="#f8fafc",
            fg="#0f172a",
            bd=1,
            relief="solid",
            wrap="word",
            padx=6,
            pady=6
        )
        self.reason_text.pack(fill="x", pady=(0, 8))
        self.reason_text.insert("1.0", "Need leave due to personal work.")

        # Submit Leave Request Button
        self.submit_leave_btn = tk.Button(
            leave_card,
            text="Submit Leave Request to Supabase",
            font=("Segoe UI", 9, "bold"),
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            relief="flat",
            pady=5,
            cursor="hand2",
            command=self.submit_leave_request
        )
        self.submit_leave_btn.pack(fill="x")

        self.leave_msg_lbl = tk.Label(
            leave_card,
            text="",
            font=("Segoe UI", 8),
            bg="#ffffff",
            fg="#16a34a"
        )
        self.leave_msg_lbl.pack(anchor="w", pady=(3, 0))

        # 4. Bottom Controls: Punch Out & Logout
        bottom_frame = tk.Frame(content, bg="#f8fafc")
        bottom_frame.pack(fill="x", pady=(2, 0))

        logout_btn = tk.Button(
            bottom_frame,
            text="🚪 Punch Out & Logout",
            font=("Segoe UI", 10, "bold"),
            bg="#dc2626",
            fg="white",
            activebackground="#b91c1c",
            activeforeground="white",
            relief="flat",
            pady=7,
            cursor="hand2",
            command=self.confirm_official_logout
        )
        logout_btn.pack(fill="x")

        note_lbl = tk.Label(
            bottom_frame,
            text="🔒 Monitoring runs in background. Close/Cancel is restricted.",
            font=("Segoe UI", 8),
            fg="#94a3b8",
            bg="#f8fafc"
        )
        note_lbl.pack(pady=(4, 0))

    def set_leave_date(self, val):
        self.leave_date_entry.delete(0, tk.END)
        self.leave_date_entry.insert(0, val)

    def submit_leave_request(self):
        leave_date = self.leave_date_entry.get().strip()
        reason = self.reason_text.get("1.0", tk.END).strip()

        if not leave_date or len(leave_date) < 8:
            messagebox.showwarning("Missing Date", "Please enter a valid leave date.", parent=self.root)
            return

        if not reason:
            messagebox.showwarning("Missing Reason", "Please type your reason in the chat box.", parent=self.root)
            return

        self.submit_leave_btn.config(state="disabled", text="Submitting...")
        self.leave_msg_lbl.config(text="Saving to Supabase...", fg="#2563eb")

        def _do():
            try:
                res = requests.post(
                    f"{API_BASE_URL}/employee/leave-request",
                    json={
                        "leave_date": leave_date,
                        "leave_type": "Casual Leave",
                        "reason": reason
                    },
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    timeout=10
                )
                if res.status_code == 200:
                    self.root.after(0, self._on_leave_ok)
                else:
                    err = res.json().get("detail", res.text)
                    self.root.after(0, lambda: self._on_leave_fail(err))
            except Exception as e:
                self.root.after(0, lambda: self._on_leave_fail(str(e)))

        import threading
        threading.Thread(target=_do, daemon=True).start()

    def _on_leave_ok(self):
        self.submit_leave_btn.config(state="normal", text="Submit Leave Request to Supabase")
        self.leave_msg_lbl.config(text="✓ Leave request saved to Supabase (Pending)!", fg="#16a34a")
        messagebox.showinfo("Success", "Leave request submitted to Supabase successfully!", parent=self.root)

    def _on_leave_fail(self, err):
        self.submit_leave_btn.config(state="normal", text="Submit Leave Request to Supabase")
        self.leave_msg_lbl.config(text="Submission error", fg="#dc2626")
        messagebox.showerror("Error", f"Failed to submit leave request:\n{err}", parent=self.root)

    # ---------------- REAL-TIME LIVE SPENDING TICKER ----------------

    def update_live_tick(self):
        if self.is_signed_out:
            return

        # Read live stats from agent.py live_session.json
        if SESSION_STATUS_FILE.exists():
            try:
                with open(SESSION_STATUS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)

                self.active_seconds = float(data.get("active_seconds", self.active_seconds))
                self.idle_seconds = float(data.get("idle_seconds", self.idle_seconds))
                self.current_status = data.get("status", self.current_status)
            except Exception:
                pass
        else:
            self.active_seconds += 1.0

        # Calculate Work Time and Over Work Time
        work_sec = int(self.active_seconds)
        idle_sec = int(self.idle_seconds)

        # Over Work Time: Time spent working beyond 8 hours (28,800s)
        if work_sec > SHIFT_TARGET_SECONDS:
            over_sec = work_sec - SHIFT_TARGET_SECONDS
            self.over_time_lbl.config(text=f"+{self.format_seconds(over_sec)}", fg="#dc2626")
            self.over_status_lbl.config(text="Overtime active!", fg="#dc2626")
        else:
            self.over_time_lbl.config(text="00:00:00", fg="#7c3aed")
            remaining = SHIFT_TARGET_SECONDS - work_sec
            self.over_status_lbl.config(text=f"({self.format_seconds(remaining)} to 8h)", fg="#64748b")

        # Update labels
        self.work_time_lbl.config(text=self.format_seconds(work_sec))
        self.idle_time_lbl.config(text=self.format_seconds(idle_sec))

        # Status badge
        if self.current_status == "IDLE":
            self.status_badge.config(text="● IDLE (Away)", fg="#facc15")
        elif self.current_status == "BREAK":
            self.status_badge.config(text="● ON BREAK", fg="#60a5fa")
        else:
            self.status_badge.config(text="● ACTIVE", fg="#4ade80")

        # Re-schedule ticker after 1000ms
        self.root.after(1000, self.update_live_tick)

    def format_seconds(self, seconds):
        sec = int(seconds)
        hours = sec // 3600
        mins = (sec % 3600) // 60
        s = sec % 60
        return f"{hours:02d}:{mins:02d}:{s:02d}"

    # ---------------- CANCELLATION RESTRICTION & TAMPER LOGGING ----------------

    def on_attempt_cancel_close(self):
        """Called if user clicks the window close [X] button or presses Alt+F4."""
        self.trigger_tamper_alert("Employee attempted to cancel or close monitoring window")

    def trigger_tamper_alert(self, reason):
        """Logs cancel attempt to Supabase and shows alert error popup."""
        def _report():
            try:
                requests.post(
                    f"{API_BASE_URL}/employee/cancel-attempt",
                    json={
                        "reason": reason,
                        "details": {
                            "active_seconds": round(self.active_seconds),
                            "idle_seconds": round(self.idle_seconds),
                            "timestamp": datetime.now().isoformat()
                        }
                    },
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    timeout=5
                )
            except Exception as e:
                print("FAILED TO LOG CANCEL ATTEMPT:", e)

        import threading
        threading.Thread(target=_report, daemon=True).start()

        # Display Corporate Alert Error
        messagebox.showerror(
            "TCS Monitoring - Cancel Error",
            "POLICY ERROR: MONITORING CANNOT BE CANCELLED!\n\n"
            "You cannot cancel or close the monitoring service during work shift.\n"
            "This cancellation attempt has been logged into the Supabase database.\n\n"
            "Use 'Punch Out & Logout' to safely end your shift.",
            parent=self.root
        )

    # ---------------- OFFICIAL LOGOUT ----------------

    def confirm_official_logout(self):
        confirm = messagebox.askyesno(
            "Confirm Logout",
            f"Are you sure you want to punch out and logout, {self.full_name}?\n\n"
            f"Work Time: {self.format_seconds(self.active_seconds)}\n"
            f"Idle Time: {self.format_seconds(self.idle_seconds)}",
            parent=self.root
        )
        if not confirm:
            return

        self.is_signed_out = True
        self.logout_time_str = datetime.now().strftime("%I:%M:%S %p")
        self.logout_lbl.config(text=self.logout_time_str, fg="#dc2626")

        # Set authorized signout flag so agent knows it's legitimate
        try:
            with open(AUTH_SIGNOUT_FLAG, "w", encoding="utf-8") as f:
                f.write(f"Authorized logout at {datetime.now().isoformat()} by {self.user_id}")
        except Exception:
            pass

        # Send punch-out to Supabase
        try:
            requests.post(
                f"{API_BASE_URL}/employee/attendance/check-out",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=5
            )
        except Exception:
            pass

        # Terminate agent
        if self.agent_process:
            try:
                self.agent_process.terminate()
            except Exception:
                pass

        messagebox.showinfo("Logged Out", f"Attendance Punch-Out successful!\nLogout Time: {self.logout_time_str}", parent=self.root)
        self.root.destroy()


def open_employee_dashboard(root, access_token, user_id, full_name, agent_process=None):
    for widget in root.winfo_children():
        widget.destroy()

    app = EmployeeDashboard(root, access_token, user_id, full_name, agent_process)
    return app
