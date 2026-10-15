import tkinter as tk
from tkinter import ttk, messagebox
import requests
import new_employe
import employee_profile

API_BASE_URL = "http://127.0.0.1:8002"


def open_dashboard(root, access_token, user_id, full_name):
    for widget in root.winfo_children():
        widget.destroy()

    root.title("Attendance Monitor - Admin Dashboard")
    root.geometry("850x550")
    root.configure(bg="#f3f5f9")

    tk.Label(
        root,
        text="Admin Dashboard",
        font=("Segoe UI", 22, "bold"),
        bg="#f3f5f9",
        fg="#172554"
    ).pack(pady=(20, 5))

    tk.Label(
        root,
        text=f"Welcome, {full_name} | Admin ID: {user_id}",
        font=("Segoe UI", 11),
        bg="#f3f5f9"
    ).pack(pady=5)

    def open_employee_form():
        new_employe.open_create_employee(root, access_token)

    def view_all_employees():
        for widget in root.winfo_children():
            widget.destroy()

        root.title("All Employees")
        root.geometry("900x550")
        root.configure(bg="#f3f5f9")

        tk.Label(
            root,
            text="All Employees",
            font=("Segoe UI", 20, "bold"),
            bg="#f3f5f9",
            fg="#172554"
        ).pack(pady=15)

        # Show a message above the table when the API returns an error or no rows.
        status_label = tk.Label(
            root,
            text="Loading employees...",
            font=("Segoe UI", 10),
            bg="#f3f5f9",
            fg="#334155"
        )
        status_label.pack(pady=(0, 5))

        columns = ("user_id", "full_name", "role", "status")
        table = ttk.Treeview(root, columns=columns, show="headings")

        table.heading("user_id", text="Employee ID")
        table.heading("full_name", text="Full Name")
        table.heading("role", text="Role")
        table.heading("status", text="Account Status")

        table.column("user_id", width=150, anchor="center")
        table.column("full_name", width=250)
        table.column("role", width=150, anchor="center")
        table.column("status", width=150, anchor="center")

        table.pack(fill="both", expand=True, padx=20, pady=10)

        def open_selected_employee_profile(event=None):
            selected_items = table.selection()
            if not selected_items:
                return

            employee_data = table.item(selected_items[0], "values")
            if not employee_data or not employee_data[0]:
                messagebox.showerror(
                    "Invalid Employee",
                    "Employee ID is missing.",
                    parent=root
                )
                return

            employee_profile.open_employee_profile(
                root, access_token, str(employee_data[0])
            )

        table.bind("<Double-1>", open_selected_employee_profile)

        def load_employees():
            status_label.config(text="Loading employees...")
            for item in table.get_children():
                table.delete(item)

            try:
                response = requests.get(
                    f"{API_BASE_URL}/admin/users",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=15
                )

                # Include the backend response so the actual cause is visible.
                if response.status_code == 401:
                    status_label.config(text="Login expired.")
                    messagebox.showerror(
                        "Login Expired",
                        "Your login token is invalid or expired. Please log in again.",
                        parent=root
                    )
                    return

                if response.status_code == 403:
                    status_label.config(text="Admin access denied.")
                    messagebox.showerror(
                        "Access Denied",
                        "This account does not have admin permission.",
                        parent=root
                    )
                    return

                if not response.ok:
                    status_label.config(text=f"API error: HTTP {response.status_code}")
                    messagebox.showerror(
                        "API Error",
                        f"GET /admin/users returned HTTP {response.status_code}.\n\n"
                        f"Backend response:\n{response.text[:1500]}",
                        parent=root
                    )
                    return

                try:
                    result = response.json()
                except ValueError:
                    status_label.config(text="Backend returned invalid JSON.")
                    messagebox.showerror(
                        "Data Error",
                        f"The backend did not return JSON.\n\n{response.text[:1000]}",
                        parent=root
                    )
                    return

                employees = result.get("users")
                if not isinstance(employees, list):
                    status_label.config(text="Unexpected API response.")
                    messagebox.showerror(
                        "Data Error",
                        "Expected response format: {'users': [...]}.\n\n"
                        f"Received:\n{result}",
                        parent=root
                    )
                    return

                valid_count = 0
                for employee in employees:
                    if not isinstance(employee, dict):
                        continue

                    employee_id = employee.get("user_id")
                    if not employee_id or str(employee_id).strip().lower() == "none":
                        continue

                    table.insert(
                        "",
                        "end",
                        values=(
                            str(employee_id),
                            employee.get("full_name") or "",
                            employee.get("role") or "",
                            "Active" if employee.get("is_active") else "Inactive"
                        )
                    )
                    valid_count += 1

                if valid_count == 0:
                    status_label.config(
                        text="API connected, but no employee records were returned."
                    )
                else:
                    status_label.config(text=f"Loaded {valid_count} employee(s).")

            except requests.RequestException as exc:
                status_label.config(text="Could not connect to backend.")
                messagebox.showerror(
                    "Connection Error",
                    f"Could not reach {API_BASE_URL}.\n\n"
                    f"Check that FastAPI is running.\n\nDetails: {exc}",
                    parent=root
                )

        controls = tk.Frame(root, bg="#f3f5f9")
        controls.pack(pady=(0, 8))

        tk.Button(
            controls,
            text="Refresh Employees",
            command=load_employees,
            bg="#2563eb",
            fg="white",
            font=("Segoe UI", 10, "bold")
        ).pack(side="left", padx=6)

        tk.Button(
            controls,
            text="Back to Dashboard",
            command=lambda: open_dashboard(
                root, access_token, user_id, full_name
            )
        ).pack(side="left", padx=6)

        load_employees()

    def view_idle_sessions():
        for widget in root.winfo_children():
            widget.destroy()

        root.title("Employee Idle Sessions")
        root.geometry("900x550")
        root.configure(bg="#f3f5f9")

        tk.Label(
            root,
            text="Employee Idle Sessions",
            font=("Segoe UI", 20, "bold"),
            bg="#f3f5f9",
            fg="#172554"
        ).pack(pady=15)

        status_label = tk.Label(
            root,
            text="Loading idle sessions...",
            font=("Segoe UI", 10),
            bg="#f3f5f9",
            fg="#334155"
        )
        status_label.pack(pady=(0, 5))

        columns = ("user_id", "duration", "seconds", "recorded_at")
        table = ttk.Treeview(root, columns=columns, show="headings")

        table.heading("user_id", text="Employee ID")
        table.heading("duration", text="Idle Duration")
        table.heading("seconds", text="Seconds")
        table.heading("recorded_at", text="Recorded At")

        table.column("user_id", width=160, anchor="center")
        table.column("duration", width=160, anchor="center")
        table.column("seconds", width=120, anchor="center")
        table.column("recorded_at", width=260, anchor="w")

        table.pack(fill="both", expand=True, padx=20, pady=10)

        def load_idle():
            status_label.config(text="Loading idle sessions from database...")
            for item in table.get_children():
                table.delete(item)

            try:
                response = requests.get(
                    f"{API_BASE_URL}/admin/idle-sessions",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=15
                )

                if not response.ok:
                    status_label.config(text=f"API error: HTTP {response.status_code}")
                    return

                data = response.json()
                sessions = data.get("idle_sessions", [])
                if not isinstance(sessions, list):
                    sessions = []

                for row in sessions:
                    u_id = row.get("username") or row.get("user_id") or "Unknown"
                    sec = int(row.get("idle_seconds") or row.get("duration_seconds") or 0)
                    m, s = divmod(sec, 60)
                    h, m = divmod(m, 60)
                    dur_str = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
                    rec_at = str(row.get("recorded_at") or row.get("idle_start") or "").replace("T", " ").split(".")[0]

                    table.insert("", "end", values=(u_id, dur_str, f"{sec}s", rec_at))

                if sessions:
                    status_label.config(text=f"Loaded {len(sessions)} idle record(s) from Supabase.")
                else:
                    status_label.config(text="No idle sessions recorded yet.")

            except Exception as exc:
                status_label.config(text=f"Error loading idle records: {exc}")

        controls = tk.Frame(root, bg="#f3f5f9")
        controls.pack(pady=(0, 8))

        tk.Button(
            controls,
            text="Refresh",
            command=load_idle,
            bg="#2563eb",
            fg="white",
            font=("Segoe UI", 10, "bold")
        ).pack(side="left", padx=6)

        tk.Button(
            controls,
            text="Back to Dashboard",
            command=lambda: open_dashboard(
                root, access_token, user_id, full_name
            ),
            bg="#64748b",
            fg="white",
            font=("Segoe UI", 10, "bold")
        ).pack(side="left", padx=6)

        load_idle()

    def view_leave_requests():
        for widget in root.winfo_children():
            widget.destroy()

        root.title("Employee Leave Requests")
        root.geometry("980x600")
        root.configure(bg="#f3f5f9")

        tk.Label(
            root,
            text="Employee Leave Requests (Supabase)",
            font=("Segoe UI", 20, "bold"),
            bg="#f3f5f9",
            fg="#172554"
        ).pack(pady=15)

        status_label = tk.Label(
            root,
            text="Loading leave requests from Supabase...",
            font=("Segoe UI", 10),
            bg="#f3f5f9",
            fg="#334155"
        )
        status_label.pack(pady=(0, 5))

        columns = ("user_id", "name", "date", "type", "reason", "status")
        table = ttk.Treeview(root, columns=columns, show="headings", selectmode="browse")

        table.heading("user_id", text="Emp ID")
        table.heading("name", text="Employee Name")
        table.heading("date", text="Leave Date")
        table.heading("type", text="Type")
        table.heading("reason", text="Reason (Chat Box)")
        table.heading("status", text="Status")

        table.column("user_id", width=100, anchor="center")
        table.column("name", width=150, anchor="w")
        table.column("date", width=110, anchor="center")
        table.column("type", width=110, anchor="w")
        table.column("reason", width=320, anchor="w")
        table.column("status", width=100, anchor="center")

        table.pack(fill="both", expand=True, padx=20, pady=10)

        def load_leaves():
            status_label.config(text="Loading leave requests...")
            for item in table.get_children():
                table.delete(item)

            try:
                response = requests.get(
                    f"{API_BASE_URL}/admin/leave-requests",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10
                )
                if response.ok:
                    items = response.json().get("leave_requests", [])
                    for row in items:
                        emp_id = row.get("employee_id") or row.get("employee_user_id") or ""
                        table.insert("", "end", values=(
                            emp_id,
                            row.get("employee_name") or emp_id,
                            row.get("leave_date") or "",
                            row.get("leave_type") or "Casual Leave",
                            row.get("reason") or "",
                            row.get("status") or "Pending"
                        ))
                    status_label.config(text=f"Loaded {len(items)} leave request(s) from Supabase.")
                else:
                    status_label.config(text="Failed to fetch leave requests.")
            except Exception as e:
                status_label.config(text=f"Error: {e}")

        def decide(decision):
            sel = table.selection()
            if not sel:
                messagebox.showwarning("Select Request", "Please select a leave request from the table.")
                return
            vals = table.item(sel[0], "values")
            emp_id = vals[0]
            leave_date = vals[2]
            try:
                res = requests.post(
                    f"{API_BASE_URL}/admin/leave-requests/decision",
                    json={"employee_id": emp_id, "leave_date": leave_date, "decision": decision},
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10
                )
                if res.ok:
                    messagebox.showinfo("Success", f"Leave request for {emp_id} ({leave_date}) marked as {decision}!")
                    load_leaves()
                else:
                    messagebox.showerror("Error", res.text)
            except Exception as e:
                messagebox.showerror("Error", str(e))

        controls = tk.Frame(root, bg="#f3f5f9")
        controls.pack(pady=(0, 12))

        tk.Button(controls, text="✓ Approve", command=lambda: decide("Approved"), bg="#16a34a", fg="white", font=("Segoe UI", 10, "bold"), padx=12, pady=4).pack(side="left", padx=6)
        tk.Button(controls, text="✗ Reject", command=lambda: decide("Rejected"), bg="#dc2626", fg="white", font=("Segoe UI", 10, "bold"), padx=12, pady=4).pack(side="left", padx=6)
        tk.Button(controls, text="🔄 Refresh", command=load_leaves, bg="#2563eb", fg="white", font=("Segoe UI", 10, "bold"), padx=12, pady=4).pack(side="left", padx=6)
        tk.Button(controls, text="Back to Dashboard", command=lambda: open_dashboard(root, access_token, user_id, full_name), bg="#64748b", fg="white", font=("Segoe UI", 10, "bold"), padx=12, pady=4).pack(side="left", padx=6)

        load_leaves()

    def view_tamper_alerts():
        for widget in root.winfo_children():
            widget.destroy()

        root.title("Workstation Cancellation & Tamper Alerts")
        root.geometry("980x600")
        root.configure(bg="#f3f5f9")

        tk.Label(
            root,
            text="🚨 Workstation Cancellation & Tamper Alerts",
            font=("Segoe UI", 20, "bold"),
            bg="#f3f5f9",
            fg="#991b1b"
        ).pack(pady=15)

        status_label = tk.Label(root, text="Loading tamper alerts from Supabase...", font=("Segoe UI", 10), bg="#f3f5f9", fg="#334155")
        status_label.pack(pady=(0, 5))

        columns = ("user_id", "timestamp", "reason", "action")
        table = ttk.Treeview(root, columns=columns, show="headings")
        table.heading("user_id", text="Employee ID")
        table.heading("timestamp", text="Recorded At")
        table.heading("reason", text="Cancellation Attempt Details")
        table.heading("action", text="Action")

        table.column("user_id", width=130, anchor="center")
        table.column("timestamp", width=180, anchor="center")
        table.column("reason", width=480, anchor="w")
        table.column("action", width=110, anchor="center")

        table.pack(fill="both", expand=True, padx=20, pady=10)

        def load_alerts():
            status_label.config(text="Loading alerts...")
            for item in table.get_children():
                table.delete(item)

            try:
                response = requests.get(
                    f"{API_BASE_URL}/admin/tamper-alerts",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10
                )
                if response.ok:
                    items = response.json().get("tamper_alerts", [])
                    for row in items:
                        det = row.get("details") or {}
                        ts = str(row.get("event_timestamp") or "").replace("T", " ").split(".")[0]
                        table.insert("", "end", values=(
                            row.get("employee_user_id") or row.get("username") or "",
                            ts,
                            det.get("reason", "Cancelled / Force closed"),
                            det.get("action", "BLOCKED")
                        ))
                    status_label.config(text=f"Loaded {len(items)} security incident(s) from Supabase.")
                else:
                    status_label.config(text="Could not load alerts.")
            except Exception as e:
                status_label.config(text=f"Error: {e}")

        controls = tk.Frame(root, bg="#f3f5f9")
        controls.pack(pady=(0, 12))
        tk.Button(controls, text="🔄 Refresh", command=load_alerts, bg="#2563eb", fg="white", font=("Segoe UI", 10, "bold"), padx=12, pady=4).pack(side="left", padx=6)
        tk.Button(controls, text="Back to Dashboard", command=lambda: open_dashboard(root, access_token, user_id, full_name), bg="#64748b", fg="white", font=("Segoe UI", 10, "bold"), padx=12, pady=4).pack(side="left", padx=6)

        load_alerts()

    # Admin Menu Buttons
    tk.Button(
        root,
        text="Create New Employee",
        font=("Segoe UI", 11, "bold"),
        bg="#2563eb",
        fg="white",
        cursor="hand2",
        command=open_employee_form
    ).pack(fill="x", padx=200, pady=(15, 6), ipady=6)

    tk.Button(
        root,
        text="View All Employees",
        font=("Segoe UI", 11, "bold"),
        bg="#0f766e",
        fg="white",
        cursor="hand2",
        command=view_all_employees
    ).pack(fill="x", padx=200, pady=6, ipady=6)

    tk.Button(
        root,
        text="View Idle Sessions",
        font=("Segoe UI", 11, "bold"),
        bg="#4f46e5",
        fg="white",
        cursor="hand2",
        command=view_idle_sessions
    ).pack(fill="x", padx=200, pady=6, ipady=6)

    tk.Button(
        root,
        text="📝 View Leave Requests (Chat Box & Dates)",
        font=("Segoe UI", 11, "bold"),
        bg="#0284c7",
        fg="white",
        cursor="hand2",
        command=view_leave_requests
    ).pack(fill="x", padx=200, pady=6, ipady=6)

    tk.Button(
        root,
        text="🚨 View Tamper & Cancel Alerts",
        font=("Segoe UI", 11, "bold"),
        bg="#dc2626",
        fg="white",
        cursor="hand2",
        command=view_tamper_alerts
    ).pack(fill="x", padx=200, pady=6, ipady=6)

    def logout():
        root.destroy()

    tk.Button(root, text="Logout", command=logout, font=("Segoe UI", 9), fg="#64748b", relief="flat", cursor="hand2").pack(pady=12)
