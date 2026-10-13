
import tkinter as tk
from tkinter import messagebox
import requests

API_URL = "http://127.0.0.1:8000"

# Fixed Admin ID
ADMIN_ID = "admin001"


def login():
    role = role_var.get()
    user_id = id_entry.get().strip()
    password = password_entry.get()

    if not user_id or not password:
        messagebox.showerror("Error", "Enter ID and password.")
        return

    try:
        if role == "Admin":
            if user_id != ADMIN_ID:
                messagebox.showerror(
                    "Login Failed", "Invalid Admin ID."
                )
                return

            response = requests.post(
                f"{API_URL}/admin/login",
                json={
                    "admin_id": user_id,
                    "password": password
                },
                timeout=10
            )

        else:
            response = requests.post(
                f"{API_URL}/login",
                json={
                    "username": user_id,
                    "password": password
                },
                timeout=10
            )

        if response.status_code == 200:
            data = response.json()
            messagebox.showinfo(
                "Success",
                f"{role} login successful!"
            )

            if role == "Admin":
                print("Admin token:", data.get("token"))
                # Connect admin dashboard here
            else:
                print("Employee token:", data.get("token"))
                # Connect attendance and monitoring here

        else:
            messagebox.showerror(
                "Login Failed",
                response.text
            )

    except requests.RequestException as e:
        messagebox.showerror(
            "Connection Error",
            "Backend is not running.\n" + str(e)
        )


root = tk.Tk()
root.title("Staff Monitoring Login")
root.geometry("360x330")
root.resizable(False, False)

tk.Label(
    root, text="STAFF MONITORING",
    font=("Arial", 16, "bold")
).pack(pady=18)

tk.Label(root, text="Login As").pack()

role_var = tk.StringVar(value="User")

role_menu = tk.OptionMenu(
    root, role_var, "User", "Admin"
)
role_menu.pack(pady=5)

tk.Label(root, text="User ID / Admin ID").pack()

id_entry = tk.Entry(root, width=30)
id_entry.pack(pady=5)

tk.Label(root, text="Password").pack()

password_entry = tk.Entry(
    root, width=30, show="*"
)
password_entry.pack(pady=5)

tk.Button(
    root,
    text="LOGIN",
    width=20,
    command=login
).pack(pady=18)

root.mainloop()
