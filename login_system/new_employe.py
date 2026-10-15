
import tkinter as tk
from tkinter import messagebox
import requests

API_BASE_URL = "http://127.0.0.1:8002"


def open_create_employee(root, access_token):
    # Create the employee form window
    employee_window = tk.Toplevel(root)
    employee_window.title("Create New Employee")
    employee_window.geometry("450x430")
    employee_window.configure(bg="#f3f5f9")
    employee_window.resizable(False, False)

    # Form heading
    tk.Label(
        employee_window,
        text="Create New Employee",
        font=("Segoe UI", 20, "bold"),
        bg="#f3f5f9",
        fg="#172554"
    ).pack(pady=(25, 20))

    # Employee ID field
    tk.Label(
        employee_window,
        text="Employee ID",
        font=("Segoe UI", 11),
        bg="#f3f5f9"
    ).pack(anchor="w", padx=45)

    user_id_entry = tk.Entry(employee_window, font=("Segoe UI", 11))
    user_id_entry.pack(fill="x", padx=45, pady=(5, 12))

    # Full name field
    tk.Label(
        employee_window,
        text="Full Name",
        font=("Segoe UI", 11),
        bg="#f3f5f9"
    ).pack(anchor="w", padx=45)

    full_name_entry = tk.Entry(employee_window, font=("Segoe UI", 11))
    full_name_entry.pack(fill="x", padx=45, pady=(5, 12))

    # Password field
    tk.Label(
        employee_window,
        text="Password",
        font=("Segoe UI", 11),
        bg="#f3f5f9"
    ).pack(anchor="w", padx=45)

    password_entry = tk.Entry(
        employee_window,
        font=("Segoe UI", 11),
        show="*"
    )
    password_entry.pack(fill="x", padx=45, pady=(5, 18))

    def create_employee():
        # Read values entered in the form
        user_id = user_id_entry.get().strip()
        full_name = full_name_entry.get().strip()
        password = password_entry.get()

        # Validate required fields
        if not user_id or not full_name or not password:
            messagebox.showwarning(
                "Missing Information",
                "Please fill in all fields.",
                parent=employee_window
            )
            return

        if len(password) < 8:
            messagebox.showwarning(
                "Weak Password",
                "Password must contain at least 8 characters.",
                parent=employee_window
            )
            return

        # Send employee details securely to the backend over the local API
        try:
            response = requests.post(
                f"{API_BASE_URL}/admin/users",
                headers={
                    "Authorization": f"Bearer {access_token}"
                },
                json={
                    "user_id": user_id,
                    "full_name": full_name,
                    "password": password
                },
                timeout=15
            )

            if response.status_code == 401:
                messagebox.showerror(
                    "Login Expired",
                    "Please log in again.",
                    parent=employee_window
                )
                return

            if response.status_code == 403:
                messagebox.showerror(
                    "Access Denied",
                    "Admin permission is required.",
                    parent=employee_window
                )
                return

            if response.status_code == 409:
                messagebox.showerror(
                    "Duplicate Employee",
                    "This Employee ID already exists.",
                    parent=employee_window
                )
                return

            response.raise_for_status()

            # Confirm successful creation
            messagebox.showinfo(
                "Success",
                f"Employee {user_id} created successfully!",
                parent=employee_window
            )

            # Clear fields after successful creation
            user_id_entry.delete(0, tk.END)
            full_name_entry.delete(0, tk.END)
            password_entry.delete(0, tk.END)

            employee_window.destroy()

        except requests.RequestException as exc:
            messagebox.showerror(
                "Connection Error",
                f"Could not create employee.\n{exc}",
                parent=employee_window
            )

    # Create employee button
    tk.Button(
        employee_window,
        text="Create Employee",
        font=("Segoe UI", 11, "bold"),
        bg="#2563eb",
        fg="white",
        activebackground="#1d4ed8",
        command=create_employee
    ).pack(fill="x", padx=45, ipady=8)

    # Close form button
    tk.Button(
        employee_window,
        text="Cancel",
        font=("Segoe UI", 10),
        command=employee_window.destroy
    ).pack(pady=12)
