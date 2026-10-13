
import time
import threading

from pynput import keyboard, mouse


IDLE_THRESHOLD = 60  # 60 seconds


last_activity = time.monotonic()
idle_start = None
total_idle_seconds = 0.0

lock = threading.Lock()
running = True


def record_activity():
    global last_activity, idle_start, total_idle_seconds

    now = time.monotonic()

    with lock:
        if idle_start is not None:
            total_idle_seconds += now - idle_start
            idle_start = None

        last_activity = now


def on_key_press(key):
    record_activity()


def on_mouse_move(x, y):
    record_activity()


def on_mouse_click(x, y, button, pressed):
    if pressed:
        record_activity()


def on_mouse_scroll(x, y, dx, dy):
    record_activity()


keyboard_listener = keyboard.Listener(
    on_press=on_key_press
)

mouse_listener = mouse.Listener(
    on_move=on_mouse_move,
    on_click=on_mouse_click,
    on_scroll=on_mouse_scroll
)


def format_time(seconds):
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60

    return f"{hours:02}:{minutes:02}:{remaining_seconds:02}"


def main():
    global idle_start, running

    keyboard_listener.start()
    mouse_listener.start()

    print("Idle tracker started.")
    print("Idle threshold: 60 seconds")
    print("Press Ctrl+C to stop.\n")

    try:
        while running:
            now = time.monotonic()

            with lock:
                inactive_seconds = now - last_activity

                if (
                    idle_start is None
                    and inactive_seconds >= IDLE_THRESHOLD
                ):
                    # Count idle time from the last activity.
                    idle_start = last_activity

                if idle_start is not None:
                    current_idle = now - idle_start
                    status = "IDLE"
                else:
                    current_idle = 0
                    status = "ACTIVE"

                total_idle = (
                    total_idle_seconds + current_idle
                )

            print(
                f"\rStatus: {status} | "
                f"Current idle: {format_time(current_idle)} | "
                f"Total idle: {format_time(total_idle)}",
                end="",
                flush=True
            )

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nIdle tracker stopped.")

    finally:
        running = False
        keyboard_listener.stop()
        mouse_listener.stop()

        with lock:
            final_total = total_idle_seconds

            if idle_start is not None:
                final_total += time.monotonic() - idle_start

        print(
            "Total idle time:",
            format_time(final_total)
        )


if __name__ == "__main__":
    main()
