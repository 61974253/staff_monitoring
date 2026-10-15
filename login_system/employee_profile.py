
import tkinter as tk
from tkinter import ttk, messagebox
import requests

# Backend API URL
API_BASE_URL = "http://127.0.0.1:8002"


def open_employee_profile(root, access_token, employee_id):
    # Create the employee profile window
    profile_window = tk.Toplevel(root)
    profile_window.title(f"Employee Profile - {employee_id}")
    profile_window.geometry("760x560")
    profile_window.configure(bg="#f3f5f9")

    # Profile heading
    tk.Label(
        profile_window,
        text=f"Employee Profile: {employee_id}",
        font=("Segoe UI", 18, "bold"),
        bg="#f3f5f9",
        fg="#172554"
    ).pack(pady=(16, 8))

    # Employee details section
    details_frame = tk.LabelFrame(
        profile_window,
        text="Employee Details",
        font=("Segoe UI", 10, "bold"),
        bg="white",
        fg="#172554",
        padx=14,
        pady=10
    )
    details_frame.pack(fill="x", padx=20, pady=8)

    details_label = tk.Label(
        details_frame,
        text="Loading employee details...",
        font=("Segoe UI", 11),
        bg="white",
        justify="left",
        anchor="w"
    )
    details_label.pack(fill="x")

    # Notebook with tabs for Attendance and Idle History
    notebook = ttk.Notebook(profile_window)
    notebook.pack(fill="both", expand=True, padx=20, pady=8)

    # Tab 1: Attendance History
    att_frame = tk.Frame(notebook, bg="#f3f5f9")
    notebook.add(att_frame, text="Attendance History")

    columns = ("date", "check_in", "check_out")
    table = ttk.Treeview(
        att_frame,
        columns=columns,
        show="headings"
    )
    table.heading("date", text="Date")
    table.heading("check_in", text="Attendance In")
    table.heading("check_out", text="Attendance Out")
    table.column("date", width=180, anchor="w")
    table.column("check_in", width=220, anchor="w")
    table.column("check_out", width=220, anchor="w")

    att_scroll = ttk.Scrollbar(att_frame, orient="vertical", command=table.yview)
    table.configure(yscrollcommand=att_scroll.set)
    table.pack(side="left", fill="both", expand=True)
    att_scroll.pack(side="right", fill="y")

    # Tab 2: Idle Time History
    idle_frame = tk.Frame(notebook, bg="#f3f5f9")
    notebook.add(idle_frame, text="Idle Time History")

    idle_columns = ("recorded_at", "duration", "seconds")
    idle_table = ttk.Treeview(
        idle_frame,
        columns=idle_columns,
        show="headings"
    )
    idle_table.heading("recorded_at", text="Recorded At")
    idle_table.heading("duration", text="Idle Duration")
    idle_table.heading("seconds", text="Seconds")
    idle_table.column("recorded_at", width=260, anchor="w")
    idle_table.column("duration", width=180, anchor="center")
    idle_table.column("seconds", width=150, anchor="center")

    idle_scroll = ttk.Scrollbar(idle_frame, orient="vertical", command=idle_table.yview)
    idle_table.configure(yscrollcommand=idle_scroll.set)
    idle_table.pack(side="left", fill="both", expand=True)
    idle_scroll.pack(side="right", fill="y")

    # Status message
    status_label = tk.Label(
        profile_window,
        text="",
        font=("Segoe UI", 9),
        bg="#f3f5f9",
        fg="#475569"
    )
    status_label.pack(anchor="w", padx=22, pady=(0, 8))

    def load_profile():
        # Clear old rows before loading again
        for item in table.get_children():
            table.delete(item)
        for item in idle_table.get_children():
            idle_table.delete(item)

        status_label.config(text="Loading profile and attendance...")

        try:
            # Request employee profile, attendance, and idle time from FastAPI
            response = requests.get(
                f"{API_BASE_URL}/admin/users/{employee_id}/attendance",
                headers={
                    "Authorization": f"Bearer {access_token}"
                },
                timeout=15
            )

            if response.status_code == 401:
                status_label.config(text="Login expired.")
                messagebox.showerror(
                    "Login Expired",
                    "Please log in again.",
                    parent=profile_window
                )
                return

            if response.status_code == 403:
                status_label.config(text="Access denied.")
                messagebox.showerror(
                    "Access Denied",
                    "Admin permission is required.",
                    parent=profile_window
                )
                return

            if response.status_code == 404:
                status_label.config(text="Employee not found.")
                messagebox.showerror(
                    "Employee Not Found",
                    f"Employee ID {employee_id} was not found.",
                    parent=profile_window
                )
                return

            if not response.ok:
                status_label.config(
                    text=f"API error: HTTP {response.status_code}"
                )
                messagebox.showerror(
                    "API Error",
                    f"HTTP {response.status_code}\n\n"
                    f"{response.text[:1200]}",
                    parent=profile_window
                )
                return

            # Convert JSON response into Python data
            data = response.json()

            employee = data.get("employee", {})
            if not isinstance(employee, dict):
                employee = {}

            attendance_records = data.get("attendance", [])
            if not isinstance(attendance_records, list):
                attendance_records = []

            idle_records = data.get("idle_records", [])
            if not isinstance(idle_records, list):
                idle_records = []

            total_idle = int(data.get("total_idle_seconds") or 0)
            hours = total_idle // 3600
            mins = (total_idle % 3600) // 60
            secs = total_idle % 60
            if hours > 0:
                idle_formatted = f"{hours}h {mins}m {secs}s ({total_idle} seconds)"
            elif mins > 0:
                idle_formatted = f"{mins}m {secs}s ({total_idle} seconds)"
            else:
                idle_formatted = f"{secs} seconds"

            # Display employee details including idle statistics
            details_label.config(
                text=(
                    f"Employee ID: {employee.get('user_id', employee_id)}\n"
                    f"Full Name: {employee.get('full_name') or 'Not available'}\n"
                    f"Role: {employee.get('role') or 'Not available'}\n"
                    f"Account Status: {'Active' if employee.get('is_active') else 'Inactive'}\n"
                    f"Total Idle Time: {idle_formatted}"
                )
            )

            # Display attendance records
            for record in attendance_records:
                if not isinstance(record, dict):
                    continue

                attendance_in = record.get("attendance_in") or ""
                attendance_out = record.get("attendance_out") or ""
                timestamp = attendance_in or attendance_out
                date_value = str(timestamp).split("T")[0] if timestamp else ""

                table.insert(
                    "",
                    "end",
                    values=(
                        date_value,
                        attendance_in,
                        attendance_out
                    )
                )

            # Display idle records
            for record in idle_records:
                if not isinstance(record, dict):
                    continue

                recorded_at = str(record.get("recorded_at") or "").replace("T", " ").split(".")[0]
                idle_sec = int(record.get("idle_seconds") or 0)
                m, s = divmod(idle_sec, 60)
                h, m = divmod(m, 60)
                duration_str = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

                idle_table.insert(
                    "",
                    "end",
                    values=(
                        recorded_at,
                        duration_str,
                        f"{idle_sec}s"
                    )
                )

            status_label.config(
                text=(
                    f"Loaded details, {len(attendance_records)} attendance record(s), "
                    f"and {len(idle_records)} idle record(s)."
                )
            )

        except requests.RequestException as exc:
            details_label.config(
                text="Could not load employee profile."
            )

            status_label.config(
                text="Backend connection failed."
            )

            messagebox.showerror(
                "Connection Error",
                f"Could not load employee details:\n{exc}",
                parent=profile_window
            )

        except (ValueError, TypeError) as exc:
            status_label.config(
                text="Unexpected response format."
            )

            messagebox.showerror(
                "Data Error",
                f"The backend returned an unexpected response:\n{exc}",
                parent=profile_window
            )

    # Refresh button
    controls = tk.Frame(
        profile_window,
        bg="#f3f5f9"
    )
    controls.pack(pady=(0, 12))

    tk.Button(
        controls,
        text="Refresh",
        command=load_profile,
        bg="#2563eb",
        fg="white",
        font=("Segoe UI", 10, "bold")
    ).pack(side="left", padx=6)

    # Close profile window
    tk.Button(
        controls,
        text="Close",
        command=profile_window.destroy
    ).pack(side="left", padx=6)

    # Load profile when the window opens
    load_profile()
