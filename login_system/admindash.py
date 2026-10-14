import tkinter as tk
from tkinter import ttk, messagebox
import requests
import new_employe
import employee_profile

API_BASE_URL = "http://127.0.0.1:8000"


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

    tk.Button(
        root,
        text="Create New Employee",
        font=("Segoe UI", 12, "bold"),
        bg="#2563eb",
        fg="white",
        command=open_employee_form
    ).pack(fill="x", padx=180, pady=(25, 10), ipady=8)

    tk.Button(
        root,
        text="View All Employees",
        font=("Segoe UI", 12, "bold"),
        bg="#0f766e",
        fg="white",
        command=view_all_employees
    ).pack(fill="x", padx=180, pady=10, ipady=8)

    def logout():
        root.destroy()

    tk.Button(root, text="Logout", command=logout).pack(pady=15)
