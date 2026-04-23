import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
from datetime import datetime, timedelta
import threading
import os
import json
import ttkbootstrap as ttk
from PIL import Image, ImageTk
import webbrowser
import pystray
from pystray import MenuItem as item
import sys
import winshell
from win32com.client import Dispatch
from win10toast import ToastNotifier
import pygame

# ---------- Paths and sound setup ----------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Create Sound Alert Folder
SOUND_DIR = os.path.join(BASE_DIR, "sound")
os.makedirs(SOUND_DIR, exist_ok=True)

# Init pygame mixer for mp3/wav
pygame.mixer.init()

# ---------- User settings ----------

default_settings = {
    "start_time": "08:00",
    "end_time": "20:00",
    "interval": 60,  # in minutes
    "daily_goal": 2.0,  # in liters
    "reminder_amount": 0.25,  # in liters
    "start_with_windows": False,
    "sound_file": "cute-gugu-gaga.mp3"
}

settings_file = "settings.json"
if os.path.exists(settings_file):
    with open(settings_file, "r") as f:
        user_settings = json.load(f)
else:
    user_settings = default_settings.copy()

for k, v in default_settings.items():
    user_settings.setdefault(k, v)

log_file = "water_intake_log.txt"


def save_user_settings():
    with open(settings_file, "w") as f:
        json.dump(user_settings, f)


# ---------- Start with Windows ----------

def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def add_to_startup():
    startup = winshell.startup()

    if getattr(sys, "frozen", False):
        exe_path = sys.executable
    else:
        exe_path = os.path.abspath(__file__)
    
    shortcut_path = os.path.join(startup, "WaterReminder.lnk")

    shell = Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.Targetpath = exe_path
    shortcut.WorkingDirectory = os.path.dirname(exe_path)
    shortcut.IconLocation = exe_path
    shortcut.save()


def remove_from_startup():
    startup = winshell.startup()
    shortcut_path = os.path.join(startup, "WaterReminder.lnk")
    if os.path.exists(shortcut_path):
        os.remove(shortcut_path)


# ---------- Main App Class ----------

class WaterReminderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Water Reminder")

        # Add app icon
        self.root.iconphoto(False, tk.PhotoImage(file=resource_path("Icon.png")))

        # Set minimum size
        self.root.minsize(500, 800)

        # Center the window on the screen
        window_width = 400
        window_height = 400
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Configure grid to make components responsive
        for c in range(4):
            self.root.grid_columnconfigure(c, weight=1)
        for r in range(15):
            self.root.grid_rowconfigure(r, weight=1)

        # Logo
        self.logo_image = Image.open(resource_path("logo.png"))
        self.logo_image = self.logo_image.resize((300, 150), Image.Resampling.LANCZOS)
        self.logo_photo = ImageTk.PhotoImage(self.logo_image)
        self.logo_label = tk.Label(root, image=self.logo_photo)
        self.logo_label.grid(row=0, column=0, padx=10, pady=10, columnspan=4)

        # State
        self.total_water_drank = 0.0
        self.daily_goal = user_settings["daily_goal"]
        self.next_reminder_time = None
        self.last_drink_time = datetime.now()

        # Build UI
        self.create_widgets()
        self.update_water_drank_label()
        self.update_remaining_label()
        self.display_log_messages()

        # Close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # System Tray Icon
        self.tray_icon = pystray.Icon("WaterReminderApp")
        self.tray_image = Image.open(resource_path("Icon.png"))
        self.tray_icon.icon = self.tray_image
        self.tray_icon.menu = pystray.Menu(
            item('Open', self.show_window),
            item('Quit', self.on_closing_tray)
        )

        # Windows Notification
        self.notifier = ToastNotifier()

        # Start reminder logic
        self.schedule_initial_reminder()

    # ---------- UI ----------

    def create_widgets(self):
        # Start Time
        tk.Label(self.root, text="Start Time (HH:MM)").grid(
            row=1, column=0, sticky=tk.W, padx=10, pady=5
        )
        self.start_time_entry = ttk.Entry(self.root)
        self.start_time_entry.insert(0, user_settings["start_time"])
        self.start_time_entry.grid(row=1, column=1, padx=10, pady=5)

        # End Time
        tk.Label(self.root, text="End Time (HH:MM)").grid(
            row=2, column=0, sticky=tk.W, padx=10, pady=5
        )
        self.end_time_entry = ttk.Entry(self.root)
        self.end_time_entry.insert(0, user_settings["end_time"])
        self.end_time_entry.grid(row=2, column=1, padx=10, pady=5)

        # Interval
        tk.Label(self.root, text="Interval (minutes)").grid(
            row=3, column=0, sticky=tk.W, padx=10, pady=5
        )
        self.interval_entry = ttk.Entry(self.root)
        self.interval_entry.insert(0, user_settings["interval"])
        self.interval_entry.grid(row=3, column=1, padx=10, pady=5)

        # Daily Goal
        tk.Label(self.root, text="Daily Goal (liters)").grid(
            row=4, column=0, sticky=tk.W, padx=10, pady=5
        )
        self.daily_goal_entry = ttk.Entry(self.root)
        self.daily_goal_entry.insert(0, user_settings["daily_goal"])
        self.daily_goal_entry.grid(row=4, column=1, padx=10, pady=5)

        # Reminder Amount
        tk.Label(self.root, text="Reminder Amount (liters)").grid(
            row=5, column=0, sticky=tk.W, padx=10, pady=5
        )
        self.reminder_amount_entry = ttk.Entry(self.root)
        self.reminder_amount_entry.insert(0, user_settings["reminder_amount"])
        self.reminder_amount_entry.grid(row=5, column=1, padx=10, pady=5)

        # Alert sound
        tk.Label(self.root, text="Alert sound").grid(
            row=6, column=0, sticky=tk.W, padx=10, pady=5
        )
        self.sound_label = tk.Label(
            self.root,
            text=user_settings["sound_file"] or "Default / None"
        )
        self.sound_label.grid(row=6, column=1, padx=10, pady=5, sticky=tk.W)
        self.browse_sound_button = ttk.Button(
            self.root, text="Browse", command=self.choose_sound_file
        )
        self.browse_sound_button.grid(row=6, column=2, padx=10, pady=5, sticky=tk.EW)

        # Start with Windows
        self.start_with_windows_var = tk.BooleanVar(
            value=user_settings["start_with_windows"]
        )
        self.start_with_windows_check = ttk.Checkbutton(
            self.root,
            text="Start with Windows",
            variable=self.start_with_windows_var
        )
        self.start_with_windows_check.grid(row=7, column=0, columnspan=2, pady=5)

        # Water Drank Label
        self.water_drank_label = tk.Label(
            self.root, text=f"Water Drank: {self.total_water_drank} liters"
        )
        self.water_drank_label.grid(row=8, column=0, columnspan=3, pady=5)

        # Remaining Label
        self.remaining_label = tk.Label(self.root, text="")
        self.remaining_label.grid(row=9, column=0, columnspan=3, pady=5)

        # Countdown Label
        self.countdown_label = tk.Label(self.root, text="Next reminder in: --:--")
        self.countdown_label.grid(row=10, column=0, columnspan=3, pady=5)

        # Save Button
        self.save_button = ttk.Button(
            self.root, text="Save Settings", command=self.save_settings
        )
        self.save_button.grid(row=11, column=0, pady=10, padx=10, sticky=tk.EW)

        # Drink Water Button
        self.drink_water_button = ttk.Button(
            self.root, text="Drink Water", command=self.drink_water_action
        )
        self.drink_water_button.grid(row=11, column=1, padx=10, pady=10, sticky=tk.EW)

        # Clear Logs Button
        self.clear_logs_button = ttk.Button(
            self.root, text="Clear Logs", command=self.clear_logs_action
        )
        self.clear_logs_button.grid(row=11, column=2, padx=10, pady=10, sticky=tk.EW)

        # Log Messages
        tk.Label(self.root, text="Log Messages").grid(
            row=12, column=0, columnspan=3, sticky=tk.W, padx=10
        )
        self.log_text = scrolledtext.ScrolledText(
            self.root, wrap=tk.WORD, width=60, height=10
        )
        self.log_text.grid(row=13, column=0, columnspan=3, padx=10, pady=5, sticky=tk.NSEW)

        # Social / links
        self.social_frame = tk.Frame(self.root)
        self.social_frame.grid(row=14, column=0, columnspan=3, pady=10)

        self.github_icon = tk.Label(
            self.social_frame, text="GitHub", fg="blue", cursor="hand2"
        )
        self.github_icon.grid(row=0, column=0, padx=5)
        self.github_icon.bind(
            "<Button-1>",
            lambda e: self.open_url("https://github.com/goenyan/WaterReminder")
        )

        self.website_icon = tk.Label(
            self.social_frame, text="Website", fg="blue", cursor="hand2"
        )
        self.website_icon.grid(row=0, column=1, padx=5)
        self.website_icon.bind(
            "<Button-1>",
            lambda e: self.open_url("https://mimiakane.com/")
        )

        self.giwish_icon = tk.Label(
            self.social_frame, text="Genshin Wish Simulator", fg="blue", cursor="hand2"
        )
        self.giwish_icon.grid(row=0, column=2, padx=5)
        self.giwish_icon.bind(
            "<Button-1>",
            lambda e: self.open_url("https://giwish.mimiakane.com/")
        )

        self.hsr_icon = tk.Label(
            self.social_frame, text="HSR Warp Simulator", fg="blue", cursor="hand2"
        )
        self.hsr_icon.grid(row=0, column=3, padx=5)
        self.hsr_icon.bind(
            "<Button-1>",
            lambda e: self.open_url("https://hsrwarp.mimiakane.com/")
        )

    # ---------- UI helpers ----------

    def update_water_drank_label(self):
        self.water_drank_label.config(
            text=f"Water Drank: {self.total_water_drank} liters"
        )

    def update_remaining_label(self):
        remaining = self.daily_goal - self.total_water_drank
        self.remaining_label.config(text=f"Remaining: {remaining} liters")

    def show_settings_saved_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Settings Saved")
        dialog.iconphoto(False, tk.PhotoImage(file=resource_path("Icon.png")))
        dialog.resizable(False, False)
        dialog.grab_set()

        label = tk.Label(dialog, text="Your settings have been saved.")
        label.pack(padx=20, pady=15)

        def close_dialog():
            if dialog.winfo_exists():
                dialog.destroy()

        ok_button = ttk.Button(dialog, text="OK", command=close_dialog)
        ok_button.pack(pady=(0, 15))

        dialog.update_idletasks()
        w = dialog.winfo_width()
        h = dialog.winfo_height()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (w // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (h // 2)
        dialog.geometry(f"{w}x{h}+{x}+{y}")

        dialog.after(3000, close_dialog)

    # ---------- Settings / actions ----------

    def save_settings(self):
        user_settings["start_time"] = self.start_time_entry.get()
        user_settings["end_time"] = self.end_time_entry.get()
        user_settings["interval"] = max(1, int(self.interval_entry.get()))
        user_settings["daily_goal"] = float(self.daily_goal_entry.get())
        user_settings["reminder_amount"] = float(self.reminder_amount_entry.get())
        user_settings["start_with_windows"] = self.start_with_windows_var.get()
        save_user_settings()

        self.show_settings_saved_dialog()

        if user_settings["start_with_windows"]:
            add_to_startup()
        else:
            remove_from_startup()

    def drink_water_action(self):
        amount = float(self.reminder_amount_entry.get())
        self.total_water_drank += amount
        with open(log_file, "a") as f:
            f.write(f"{datetime.now()}: Drank {amount} liters\n")
        self.update_water_drank_label()
        self.update_remaining_label()
        self.display_log_messages()

        self.reset_timer_from_now()

    def clear_logs_action(self):
        open(log_file, 'w').close()
        self.display_log_messages()

    def display_log_messages(self):
        self.log_text.delete('1.0', tk.END)
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                log_content = f.read()
            self.log_text.insert(tk.END, log_content)

    # ---------- Timer / reminder logic ----------

    def schedule_initial_reminder(self):
        self.reset_timer_from_now()
        self.update_countdown_label()

    def reset_timer_from_now(self):
        self.last_drink_time = datetime.now()

        start_time = datetime.strptime(user_settings["start_time"], "%H:%M").time()
        end_time = datetime.strptime(user_settings["end_time"], "%H:%M").time()
        interval_minutes = max(1, int(user_settings["interval"]))
        interval = timedelta(minutes=interval_minutes)

        next_reminder_time = (self.last_drink_time + interval).replace(second=0, microsecond=0)

        if start_time <= next_reminder_time.time() <= end_time:
            self.next_reminder_time = next_reminder_time
        else:
            self.next_reminder_time = None

    def update_countdown_label(self):
        now = datetime.now()
        interval_minutes = max(1, int(user_settings["interval"]))
        interval = timedelta(minutes=interval_minutes)

        elapsed = now - self.last_drink_time

        if elapsed >= interval:
            self.send_reminder()
            self.last_drink_time = datetime.now()
            remaining = interval
        else:
            remaining = interval - elapsed

        total_seconds = int(remaining.total_seconds())
        minutes, seconds = divmod(total_seconds, 60)
        self.countdown_label.config(
            text=f"Next reminder in: {minutes:02d}:{seconds:02d}"
        )

        self.root.after(1000, self.update_countdown_label)

    def send_reminder(self):
        start_time = datetime.strptime(user_settings["start_time"], "%H:%M").time()
        end_time = datetime.strptime(user_settings["end_time"], "%H:%M").time()

        self.show_reminder_messagebox()

        now = datetime.now()

        interval_minutes = max(1, int(user_settings["interval"]))
        interval = timedelta(minutes=interval_minutes)

        next_reminder_time = (now + interval).replace(second=0, microsecond=0)

        if start_time <= next_reminder_time.time() <= end_time:
            self.next_reminder_time = next_reminder_time
        else:
            self.next_reminder_time = None
            
        self.show_reminder_messagebox()

    # ---------- Notification / sound ----------

    def show_reminder_messagebox(self):
        self.notifier.show_toast(
            "Water Reminder",
            "Time to drink water!",
            icon_path=resource_path("Icon.ico"),
            duration=5,
            threaded=True
        )

        def play_sound_with_fallback():
            preferred = user_settings.get("sound_file") or "cute-gugu-gaga.mp3"
            candidates = [preferred]
            if "cute-gugu-gaga.mp3" not in candidates:
                candidates.append("cute-gugu-gaga.mp3")

            for name in candidates:
                path = os.path.join(SOUND_DIR, name)
                if os.path.exists(path):
                    try:
                        pygame.mixer.music.stop()
                        pygame.mixer.music.load(path)
                        pygame.mixer.music.play()
                        return
                    except Exception as e:
                        with open(log_file, "a") as f:
                            f.write(
                                f"{datetime.now()}: Error playing sound {name}: {e}\n"
                            )

            with open(log_file, "a") as f:
                f.write(
                    f"{datetime.now()}: No valid sound file found. "
                    f"Tried: {candidates}\n"
                )

        threading.Thread(target=play_sound_with_fallback, daemon=True).start()

    # ---------- Misc ----------

    def open_url(self, url):
        webbrowser.open_new(url)

    def on_closing(self):
        if messagebox.askyesno(
            "Minimize to tray",
            "Do you want to minimize the app to the system tray?"
        ):
            self.hide_window()
        else:
            self.root.destroy()

    def hide_window(self):
        self.root.withdraw()
        self.tray_icon.run()

    def show_window(self, icon, item):
        self.root.deiconify()
        self.tray_icon.stop()

    def on_closing_tray(self, icon, item):
        self.root.destroy()
        self.tray_icon.stop()

    def choose_sound_file(self):
        file_path = filedialog.askopenfilename(
            title="Choose alert sound",
            initialdir=SOUND_DIR,
            filetypes=[("Audio files", "*.mp3 *.wav *.ogg"), ("All files", "*.*")]
        )
        if not file_path:
            return

        filename = os.path.basename(file_path)
        target_path = os.path.join(SOUND_DIR, filename)

        if os.path.abspath(file_path) != os.path.abspath(target_path):
            try:
                import shutil
                shutil.copy2(file_path, target_path)
            except Exception as e:
                messagebox.showerror(
                    "Error",
                    f"Could not copy sound file:\n{e}"
                )
                return

        user_settings["sound_file"] = filename
        self.sound_label.config(text=filename)
        save_user_settings()


# ---------- Main ----------

if __name__ == "__main__":
    root = ttk.Window(themename="cosmo")
    app = WaterReminderApp(root)
    root.mainloop()