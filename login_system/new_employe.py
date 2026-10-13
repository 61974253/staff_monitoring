
import tkinter as tk
from tkinter import messagebox
import requests

API_URL = "http://127.0.0.1:8000/admin/users"


def open_create_employee(parent, access_token):
    window = tk.Toplevel(parent)
    window.title("Create New Employee")
    window.geometry("400x430")
    window.resizable(False, False)
    window.configure(bg="#f3f5f9")

    tk.Label(
        window,
        text="Create New Employee",
        font=("Segoe UI", 18, "bold"),
        bg="#f3f5f9",
        fg="#172554"
    ).pack(pady=(25, 20))

    tk.Label(window, text="Employee ID", bg="#f3f5f9").pack()

    employee_id_entry = tk.Entry(
        window, font=("Segoe UI", 11), width=30
    )
    employee_id_entry.pack(pady=(5, 12), ipady=4)

    tk.Label(window, text="Full Name", bg="#f3f5f9").pack()

    full_name_entry = tk.Entry(
        window, font=("Segoe UI", 11), width=30
    )
    full_name_entry.pack(pady=(5, 12), ipady=4)

    tk.Label(window, text="Password", bg="#f3f5f9").pack()

    password_entry = tk.Entry(
        window, font=("Segoe UI", 11), width=30, show="*"
    )
    password_entry.pack(pady=(5, 12), ipady=4)

    status_label = tk.Label(
        window,
        text="Enter employee details",
        bg="#f3f5f9",
        fg="#64748b"
    )
    status_label.pack(pady=5)

    def new_employe():
        employee_id = employee_id_entry.get().strip()
        full_name = full_name_entry.get().strip()
        password = password_entry.get()

        if not employee_id or not full_name or not password:
            messagebox.showwarning(
                "Missing Details",
                "Fill in all fields.",
                parent=window
            )
            return

        create_button.config(state="disabled")
        status_label.config(text="Creating employee...")

        try:
            response = requests.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {access_token}"
                },
                json={
                    "user_id": employee_id,
                    "full_name": full_name,
                    "password": password
                },
                timeout=15
            )

            if response.status_code in (200, 201):
                messagebox.showinfo(
                    "Success",
                    f"Employee {employee_id} created successfully!",
                    parent=window
                )
                employee_id_entry.delete(0, tk.END)
                full_name_entry.delete(0, tk.END)
                password_entry.delete(0, tk.END)
                status_label.config(text="Employee created successfully")

            elif response.status_code == 401:
                messagebox.showerror(
                    "Login Expired",
                    "Please log in again.",
                    parent=window
                )

            elif response.status_code == 403:
                messagebox.showerror(
                    "Access Denied",
                    "Only an admin can create employees.",
                    parent=window
                )

            else:
                messagebox.showerror(
                    "Creation Failed",
                    f"Server response: {response.status_code}\n"
                    f"{response.text[:300]}",
                    parent=window
                )

        except requests.RequestException:
            messagebox.showerror(
                "Connection Error",
                "Cannot connect to backend. Check whether it is running.",
                parent=window
            )

        finally:
            if window.winfo_exists():
                create_button.config(state="normal")

    create_button = tk.Button(
        window,
        text="Create Employee",
        font=("Segoe UI", 11, "bold"),
        bg="#16a34a",
        fg="white",
        cursor="hand2",
        command=new_employe
    )
    create_button.pack(fill="x", padx=60, pady=(12, 8), ipady=7)

    tk.Button(
        window,
        text="Close",
        command=window.destroy
    ).pack(pady=5)

    employee_id_entry.focus_set()
