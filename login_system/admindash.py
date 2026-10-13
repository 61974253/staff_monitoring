
import tkinter as tk
from tkinter import messagebox
import new_employe


def open_dashboard(root, access_token, user_id, full_name):
    # Remove login screen widgets
    for widget in root.winfo_children():
        widget.destroy()

    root.title("Attendance Monitor - Admin Dashboard")
    root.geometry("420x320")
    root.configure(bg="#f3f5f9")

    tk.Label(
        root,
        text="Admin Dashboard",
        font=("Segoe UI", 20, "bold"),
        bg="#f3f5f9",
        fg="#172554"
    ).pack(pady=(30, 10))

    tk.Label(
        root,
        text=f"Welcome, {full_name}",
        font=("Segoe UI", 11),
        bg="#f3f5f9"
    ).pack(pady=5)

    def open_employee_form():
        new_employe.open_create_employee(
            root,
            access_token
        )

    tk.Button(
        root,
        text="Create New Employee",
        font=("Segoe UI", 12, "bold"),
        bg="#2563eb",
        fg="white",
        command=open_employee_form
    ).pack(fill="x", padx=65, pady=(30, 12), ipady=8)

    def logout():
        root.destroy()

    tk.Button(
        root,
        text="Logout",
        command=logout
    ).pack(pady=8)
