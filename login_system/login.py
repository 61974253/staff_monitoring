
import tkinter as tk
from tkinter import messagebox
import requests
import threading
import admindash

API_URL = "http://127.0.0.1:8000/login"


def admin_user():
    user_id = user_id_entry.get().strip()
    password = password_entry.get()

    if not user_id or not password:
        messagebox.showwarning(
            "Missing Details",
            "Enter User ID and Password."
        )
        return

    login_button.config(state="disabled", text="Checking...")
    status_label.config(text="Connecting to server...")

    threading.Thread(
        target=verify_login,
        args=(user_id, password),
        daemon=True
    ).start()


def verify_login(user_id, password):
    try:
        response = requests.post(
            API_URL,
            json={
                "user_id": user_id,
                "password": password
            },
            timeout=15
        )

        if response.status_code == 200:
            result = response.json()
            root.after(0, lambda: login_success(result))

        elif response.status_code == 401:
            root.after(
                0,
                lambda: login_failed(
                    "Invalid User ID or Password."
                )
            )

        else:
            root.after(
                0,
                lambda: login_failed(
                    f"Server error: {response.status_code}"
                )
            )

    except requests.RequestException:
        root.after(
            0,
            lambda: login_failed(
                "Cannot connect to backend. Check server."
            )
        )



def login_success(result):
    role = result.get("role", "").lower()
    full_name = result.get(
        "full_name",
        result.get("user_id", "User")
    )

    if role == "admin":
        status_label.config(text="Login successful!")

        messagebox.showinfo(
            "Welcome",
            f"Welcome, {full_name}!"
        )

        login_button.config(state="normal", text="Login")

        # Open admin dashboard using the existing login window
        admindash.open_dashboard(
            root,
            result.get("access_token"),
            result.get("user_id"),
            full_name
        )

    elif role == "employee":
        status_label.config(text="Employee login successful!")

        messagebox.showinfo(
            "Welcome",
            f"Welcome, {full_name}!\n"
            "Employee attendance screen is the next step."
        )

        login_button.config(state="normal", text="Login")

    else:
        login_button.config(state="normal", text="Login")
        messagebox.showerror(
            "Login Error",
            "Unknown user role. Please contact the admin."
        )

    # Attendance IN/OUT can be connected here next.


def login_failed(message):
    status_label.config(text="Login failed.")
    login_button.config(state="normal", text="Login")
    messagebox.showerror("Login Error", message)


root = tk.Tk()
root.title("Attendance Monitor - Login")
root.geometry("380x330")
root.resizable(False, False)
root.configure(bg="#f3f5f9")

title_label = tk.Label(
    root,
    text="Attendance Monitor",
    font=("Segoe UI", 18, "bold"),
    bg="#f3f5f9",
    fg="#172554"
)
title_label.pack(pady=(25, 20))

tk.Label(
    root,
    text="User ID",
    font=("Segoe UI", 10),
    bg="#f3f5f9"
).pack(anchor="w", padx=45)

user_id_entry = tk.Entry(
    root,
    font=("Segoe UI", 11),
    width=30
)
user_id_entry.pack(padx=45, pady=(5, 12), ipady=5)

tk.Label(
    root,
    text="Password",
    font=("Segoe UI", 10),
    bg="#f3f5f9"
).pack(anchor="w", padx=45)

password_entry = tk.Entry(
    root,
    font=("Segoe UI", 11),
    width=30,
    show="*"
)
password_entry.pack(padx=45, pady=(5, 18), ipady=5)

login_button = tk.Button(
    root,
    text="Login",
    font=("Segoe UI", 11, "bold"),
    bg="#2563eb",
    fg="white",
    activebackground="#1d4ed8",
    activeforeground="white",
    cursor="hand2",
    command=admin_user
)
login_button.pack(fill="x", padx=45, ipady=7)

status_label = tk.Label(
    root,
    text="Please sign in",
    font=("Segoe UI", 9),
    bg="#f3f5f9",
    fg="#64748b"
)
status_label.pack(pady=12)

password_entry.bind("<Return>", lambda event: admin_user())
user_id_entry.focus_set()

root.mainloop()
