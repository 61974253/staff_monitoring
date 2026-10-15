
import tkinter as tk
from tkinter import messagebox
import requests
import threading
import admindash
import os
import sys
import subprocess
from pathlib import Path



BACKEND_URL = "http://127.0.0.1:8002"
LOGIN_URL = f"{BACKEND_URL}/login"

BASE_DIR = Path(__file__).resolve().parent
AGENT_FILE = BASE_DIR / "agent.py"

agent_process = None
employee_access_token = None
employee_session_result = None
close_after_logout = False


def stop_employee_agent():
    global agent_process

    process = agent_process
    if process is None:
        return

    if process.poll() is None and process.stdin is not None:
        process.stdin.write("logout\n")
        process.stdin.flush()
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=5)

    if process.stdin is not None:
        process.stdin.close()
    agent_process = None
    if process.returncode not in (None, 0):
        raise RuntimeError(
            "Monitoring could not save its final activity summary. "
            "Attendance logout was not completed."
        )


def start_employee_agent(result):
    global agent_process

    # Avoid starting duplicate agent processes
    if agent_process is not None and agent_process.poll() is None:
        return

    if not AGENT_FILE.exists():
        messagebox.showerror(
            "Agent Error",
            f"agent.py not found:\n{AGENT_FILE}"
        )
        return

    # Pass login details securely through the child process environment
    agent_env = os.environ.copy()
    agent_env["EMPLOYEE_ACCESS_TOKEN"] = result.get("access_token", "")
    agent_env["EMPLOYEE_USER_ID"] = result.get("user_id", "")

    try:
        agent_process = subprocess.Popen(
            [sys.executable, str(AGENT_FILE)],
            cwd=str(BASE_DIR),
            env=agent_env,
            stdin=subprocess.PIPE,
            text=True
        )

        status_label.config(text="Employee login successful. Agent started.")

    except OSError as error:
        messagebox.showerror(
            "Agent Error",
            f"Could not start agent.py:\n{error}"
        )


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
            LOGIN_URL,
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
    global employee_access_token
    global employee_session_result

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
        employee_access_token = result.get("access_token")
        employee_session_result = result
        # Start agent after successful employee login
        start_employee_agent(result)

        login_frame.pack_forget()
        employee_name_label.config(text=f"Welcome, {full_name}")
        employee_status_label.config(text="Monitoring is active.")
        employee_dashboard.pack(fill="both", expand=True)
        status_label.config(text="Employee login successful!")

        messagebox.showinfo(
            "Welcome",
            f"Welcome, {full_name}!\n"
            "Employee login successful."
        )

    else:
        login_button.config(state="normal", text="Login")
        messagebox.showerror(
            "Login Error",
            "Unknown user role. Please contact the admin."
        )

    # Attendance IN/OUT can be connected here next.


def logout_employee():
    if not employee_access_token:
        return

    login_button.config(state="disabled")
    logout_button.config(state="disabled")
    employee_status_label.config(
        text="Stopping monitoring and ending attendance..."
    )

    threading.Thread(
        target=complete_employee_logout,
        args=(employee_access_token,),
        daemon=True
    ).start()


def complete_employee_logout(access_token):
    try:
        stop_employee_agent()
        response = requests.post(
            f"{BACKEND_URL}/logout",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15
        )
        if not response.ok:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise RuntimeError(
                detail or f"Logout failed with status {response.status_code}"
            )

        root.after(0, employee_logout_success)
    except (requests.RequestException, RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        root.after(
            0,
            lambda error_message=str(error): employee_logout_failed(
                error_message
            )
        )


def employee_logout_success():
    global employee_access_token
    global employee_session_result
    global close_after_logout

    employee_access_token = None
    employee_session_result = None
    if close_after_logout:
        close_after_logout = False
        root.destroy()
        return

    logout_button.config(state="normal")
    employee_dashboard.pack_forget()
    login_frame.pack(fill="both", expand=True)
    login_button.config(state="normal", text="Login")
    user_id_entry.delete(0, tk.END)
    password_entry.delete(0, tk.END)
    status_label.config(text="Logged out. Please sign in.")
    user_id_entry.focus_set()


def employee_logout_failed(error):
    global close_after_logout

    close_after_logout = False
    if employee_session_result:
        start_employee_agent(employee_session_result)
    logout_button.config(state="normal")
    employee_status_label.config(
        text=f"Logout failed; monitoring remains active: {error}"
    )


def login_failed(message):
    status_label.config(text="Login failed.")
    login_button.config(state="normal", text="Login")
    messagebox.showerror("Login Error", message)


root = tk.Tk()
root.title("Attendance Monitor - Login")
root.geometry("380x330")
root.resizable(False, False)
root.configure(bg="#f3f5f9")


def handle_window_close():
    if not employee_access_token:
        root.iconify()
        return

    dialog = tk.Toplevel(root)
    dialog.title("Employee session is active")
    dialog.transient(root)
    dialog.resizable(False, False)
    dialog.configure(bg="#f3f5f9")
    dialog.grab_set()

    tk.Label(
        dialog,
        text=(
            "Monitoring is active.\n\n"
            "Choose Logout and Close to stop monitoring and end attendance, "
            "or keep the app in the taskbar to continue monitoring."
        ),
        justify="left",
        wraplength=340,
        bg="#f3f5f9",
        fg="#1e293b",
        padx=20,
        pady=20
    ).pack(fill="both", expand=True)

    buttons = tk.Frame(dialog, bg="#f3f5f9")
    buttons.pack(fill="x", padx=16, pady=(0, 16))

    def logout_and_close():
        global close_after_logout
        close_after_logout = True
        dialog.destroy()
        logout_employee()

    def keep_running():
        dialog.destroy()
        root.iconify()

    tk.Button(
        buttons,
        text="Logout and Close",
        command=logout_and_close
    ).pack(side="left", expand=True, fill="x", padx=(0, 6))
    tk.Button(
        buttons,
        text="Keep Running in Taskbar",
        command=keep_running
    ).pack(side="left", expand=True, fill="x", padx=(6, 0))
    dialog.protocol("WM_DELETE_WINDOW", keep_running)
    dialog.update_idletasks()
    dialog.geometry(
        f"+{root.winfo_rootx() + 20}+{root.winfo_rooty() + 40}"
    )

root.protocol("WM_DELETE_WINDOW", handle_window_close)

login_frame = tk.Frame(root, bg="#f3f5f9")
login_frame.pack(fill="both", expand=True)

title_label = tk.Label(
    login_frame,
    text="Attendance Monitor",
    font=("Segoe UI", 18, "bold"),
    bg="#f3f5f9",
    fg="#172554"
)
title_label.pack(pady=(25, 20))

tk.Label(
    login_frame,
    text="User ID",
    font=("Segoe UI", 10),
    bg="#f3f5f9"
).pack(anchor="w", padx=45)

user_id_entry = tk.Entry(
    login_frame,
    font=("Segoe UI", 11),
    width=30
)
user_id_entry.pack(padx=45, pady=(5, 12), ipady=5)

tk.Label(
    login_frame,
    text="Password",
    font=("Segoe UI", 10),
    bg="#f3f5f9"
).pack(anchor="w", padx=45)

password_entry = tk.Entry(
    login_frame,
    font=("Segoe UI", 11),
    width=30,
    show="*"
)
password_entry.pack(padx=45, pady=(5, 18), ipady=5)

login_button = tk.Button(
    login_frame,
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
    login_frame,
    text="Please sign in",
    font=("Segoe UI", 9),
    bg="#f3f5f9",
    fg="#64748b"
)
status_label.pack(pady=12)

employee_dashboard = tk.Frame(root, bg="#f3f5f9")
tk.Label(
    employee_dashboard,
    text="Employee Dashboard",
    font=("Segoe UI", 18, "bold"),
    bg="#f3f5f9",
    fg="#172554"
).pack(pady=(55, 14))

employee_name_label = tk.Label(
    employee_dashboard,
    text="",
    font=("Segoe UI", 12),
    bg="#f3f5f9",
    fg="#334155"
)
employee_name_label.pack(pady=(0, 24))

employee_status_label = tk.Label(
    employee_dashboard,
    text="",
    font=("Segoe UI", 9),
    bg="#f3f5f9",
    fg="#64748b"
)
employee_status_label.pack(pady=(0, 12))

logout_button = tk.Button(
    employee_dashboard,
    text="Logout",
    font=("Segoe UI", 10, "bold"),
    bg="#dc2626",
    fg="white",
    activebackground="#b91c1c",
    activeforeground="white",
    cursor="hand2",
    command=logout_employee
)
logout_button.pack(fill="x", padx=45, ipady=7)

password_entry.bind("<Return>", lambda event: admin_user())
user_id_entry.focus_set()

root.mainloop()
