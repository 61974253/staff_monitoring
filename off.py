import ctypes
import ctypes.wintypes as wt
import json
import time
from datetime import datetime
from pathlib import Path

# =====================================
# CONFIGURATION
# =====================================

LOG_FILE = Path(__file__).resolve().parent / "events.jsonl"

WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
WM_WTSSESSION_CHANGE = 0x02B1

WTS_SESSION_LOCK = 0x7
WTS_SESSION_UNLOCK = 0x8

NOTIFY_FOR_THIS_SESSION = 0

LRESULT = ctypes.c_ssize_t

# =====================================
# WINDOWS API
# =====================================

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
wtsapi32 = ctypes.WinDLL("wtsapi32", use_last_error=True)

# Function signatures

kernel32.GetModuleHandleW.argtypes = [wt.LPCWSTR]
kernel32.GetModuleHandleW.restype = wt.HINSTANCE

user32.DefWindowProcW.argtypes = [
    wt.HWND,
    wt.UINT,
    wt.WPARAM,
    wt.LPARAM,
]
user32.DefWindowProcW.restype = LRESULT

user32.DestroyWindow.argtypes = [wt.HWND]
user32.DestroyWindow.restype = wt.BOOL

user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.PostQuitMessage.restype = None

wtsapi32.WTSRegisterSessionNotification.argtypes = [
    wt.HWND,
    wt.DWORD,
]
wtsapi32.WTSRegisterSessionNotification.restype = wt.BOOL

wtsapi32.WTSUnRegisterSessionNotification.argtypes = [
    wt.HWND,
]
wtsapi32.WTSUnRegisterSessionNotification.restype = wt.BOOL


# =====================================
# EVENT LOGGING
# =====================================

lock_start_time = None


def log_event(event_name, details=None):
    record = {
        "event": event_name,
        "timestamp": datetime.now().astimezone().isoformat(),
        "details": details or {},
    }

    with open(LOG_FILE, "a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")
        file.flush()

    print(record, flush=True)


# =====================================
# WINDOWS WINDOW CALLBACK
# =====================================

WNDPROC = ctypes.WINFUNCTYPE(
    LRESULT,
    wt.HWND,
    wt.UINT,
    wt.WPARAM,
    wt.LPARAM,
)


@WNDPROC
def window_proc(hwnd, msg, wparam, lparam):
    global lock_start_time

    if msg == WM_WTSSESSION_CHANGE:

        if wparam == WTS_SESSION_LOCK:
            lock_start_time = time.monotonic()
            log_event("SESSION_LOCKED")

        elif wparam == WTS_SESSION_UNLOCK:
            log_event("SESSION_UNLOCKED")

            if lock_start_time is not None:
                duration = round(
                    time.monotonic() - lock_start_time
                )

                log_event(
                    "SESSION_LOCK_DURATION",
                    {
                        "duration_seconds": duration,
                        "duration_minutes": round(
                            duration / 60, 2
                        ),
                    },
                )

                print(
                    f"Computer locked for {duration} seconds",
                    flush=True,
                )

                lock_start_time = None

        return 0

    if msg == WM_CLOSE:
        user32.DestroyWindow(hwnd)
        return 0

    if msg == WM_DESTROY:
        user32.PostQuitMessage(0)
        return 0

    return user32.DefWindowProcW(
        hwnd, msg, wparam, lparam
    )


# =====================================
# WINDOW CLASS
# =====================================

class WNDCLASS(ctypes.Structure):
    _fields_ = [
        ("style", wt.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wt.HINSTANCE),
        ("hIcon", wt.HANDLE),
        ("hCursor", wt.HANDLE),
        ("hbrBackground", wt.HANDLE),
        ("lpszMenuName", wt.LPCWSTR),
        ("lpszClassName", wt.LPCWSTR),
    ]


user32.RegisterClassW.argtypes = [
    ctypes.POINTER(WNDCLASS)
]
user32.RegisterClassW.restype = wt.ATOM

user32.CreateWindowExW.argtypes = [
    wt.DWORD,
    wt.LPCWSTR,
    wt.LPCWSTR,
    wt.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wt.HWND,
    wt.HMENU,
    wt.HINSTANCE,
    ctypes.c_void_p,
]
user32.CreateWindowExW.restype = wt.HWND

user32.GetMessageW.argtypes = [
    ctypes.POINTER(wt.MSG),
    wt.HWND,
    wt.UINT,
    wt.UINT,
]
user32.GetMessageW.restype = ctypes.c_int

user32.TranslateMessage.argtypes = [
    ctypes.POINTER(wt.MSG)
]
user32.TranslateMessage.restype = wt.BOOL

user32.DispatchMessageW.argtypes = [
    ctypes.POINTER(wt.MSG)
]
user32.DispatchMessageW.restype = LRESULT


# =====================================
# MAIN PROGRAM
# =====================================

def main():
    instance = kernel32.GetModuleHandleW(None)

    wc = WNDCLASS()
    wc.lpfnWndProc = window_proc
    wc.hInstance = instance
    wc.lpszClassName = "StaffSessionMonitorWindow"

    atom = user32.RegisterClassW(ctypes.byref(wc))

    if not atom:
        raise ctypes.WinError(ctypes.get_last_error())

    hwnd = user32.CreateWindowExW(
        0,
        wc.lpszClassName,
        "Staff Session Monitor",
        0,
        0, 0, 0, 0,
        None,
        None,
        instance,
        None,
    )

    if not hwnd:
        raise ctypes.WinError(ctypes.get_last_error())

    registered = wtsapi32.WTSRegisterSessionNotification(
        hwnd,
        NOTIFY_FOR_THIS_SESSION,
    )

    if not registered:
        error = ctypes.get_last_error()
        user32.DestroyWindow(hwnd)
        raise ctypes.WinError(error)

    log_event("SESSION_MONITOR_STARTED")

    print("\nStaff Monitoring Started!")
    print("Press Win + L to lock your computer.")
    print("Unlock it to calculate lock duration.")
    print("Press Ctrl + C here to stop.\n")

    try:
        message = wt.MSG()

        while True:
            result = user32.GetMessageW(
                ctypes.byref(message),
                None,
                0,
                0,
            )

            if result == -1:
                raise ctypes.WinError(
                    ctypes.get_last_error()
                )

            if result == 0:
                break

            user32.TranslateMessage(
                ctypes.byref(message)
            )

            user32.DispatchMessageW(
                ctypes.byref(message)
            )

    except KeyboardInterrupt:
        log_event("SESSION_MONITOR_STOPPED")

    finally:
        wtsapi32.WTSUnRegisterSessionNotification(hwnd)
        user32.DestroyWindow(hwnd)


if __name__ == "__main__":
    main()