import tkinter as tk
from tkinter import scrolledtext, messagebox
from datetime import datetime, timedelta
import sched
import time
import threading
import os
import json
import ttkbootstrap as ttk
from PIL import Image, ImageTk

# Scheduler for reminders
scheduler = sched.scheduler(time.time, time.sleep)

# User settings and defaults
default_settings = {
    "start_time": "08:00",
    "end_time": "20:00",
    "interval": 60,  # in minutes
    "daily_goal": 2.0,  # in liters
    "reminder_amount": 0.25,  # in liters
    "start_with_windows": False
}
settings_file = "settings.json"
if os.path.exists(settings_file):
    with open(settings_file, "r") as f:
        user_settings = json.load(f)
else:
    user_settings = default_settings

# Logging file
log_file = "water_intake_log.txt"

# Function to save user settings
def save_user_settings():
    with open(settings_file, "w") as f:
        json.dump(user_settings, f)

# Function to start the app with Windows
def add_to_startup():
    file_path = os.path.abspath(__file__)
    key = reg.HKEY_CURRENT_USER
    key_value = r'Software\Microsoft\Windows\CurrentVersion\Run'
    open_key = reg.OpenKey(key, key_value, 0, reg.KEY_ALL_ACCESS)
    reg.SetValueEx(open_key, "WaterReminderApp", 0, reg.REG_SZ, file_path)
    reg.CloseKey(open_key)

# Function to remove the app from startup
def remove_from_startup():
    try:
        key = reg.HKEY_CURRENT_USER
        key_value = r'Software\Microsoft\Windows\CurrentVersion\Run'
        open_key = reg.OpenKey(key, key_value, 0, reg.KEY_ALL_ACCESS)
        reg.DeleteValue(open_key, "WaterReminderApp")
        reg.CloseKey(open_key)
    except FileNotFoundError:
        pass  # If the registry key does not exist, do nothing

# HUD class
class WaterReminderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Water Reminder")

        # Add app icon
        self.root.iconphoto(False, tk.PhotoImage(file="Icon.png"))

        # Set minimum size
        self.root.minsize(400, 800)

       # Center the window on the screen
        window_width = 400
        window_height = 400
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Configure grid to make components responsive
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_columnconfigure(2, weight=1)
        self.root.grid_columnconfigure(3, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=1)
        self.root.grid_rowconfigure(3, weight=1)
        self.root.grid_rowconfigure(4, weight=1)
        self.root.grid_rowconfigure(5, weight=1)
        self.root.grid_rowconfigure(6, weight=1)
        self.root.grid_rowconfigure(7, weight=1)
        self.root.grid_rowconfigure(8, weight=1)
        self.root.grid_rowconfigure(9, weight=1)
        self.root.grid_rowconfigure(10, weight=1)

        # Add logo placeholder
        self.logo_image = Image.open("logo.png")
        self.logo_image = self.logo_image.resize((300, 150), Image.LANCZOS)  # Updated from Image.ANTIALIAS
        self.logo_photo = ImageTk.PhotoImage(self.logo_image)
        self.logo_label = tk.Label(root, image=self.logo_photo)
        self.logo_label.grid(row=0, column=0, padx=10, pady=10, columnspan=4)

        self.total_water_drank = 0.0
        self.daily_goal = user_settings["daily_goal"]

        # Create the input fields and labels
        self.create_widgets()

        self.update_water_drank_label()
        self.update_remaining_label()

        # Display log messages
        self.display_log_messages()

    def create_widgets(self):
        # Start Time
        tk.Label(self.root, text="Start Time (HH:MM)").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        self.start_time_entry = ttk.Entry(self.root)
        self.start_time_entry.insert(0, user_settings["start_time"])
        self.start_time_entry.grid(row=1, column=1, padx=10, pady=5)

        # End Time
        tk.Label(self.root, text="End Time (HH:MM)").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        self.end_time_entry = ttk.Entry(self.root)
        self.end_time_entry.insert(0, user_settings["end_time"])
        self.end_time_entry.grid(row=2, column=1, padx=10, pady=5)

        # Interval
        tk.Label(self.root, text="Interval (minutes)").grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)
        self.interval_entry = ttk.Entry(self.root)
        self.interval_entry.insert(0, user_settings["interval"])
        self.interval_entry.grid(row=3, column=1, padx=10, pady=5)

        # Daily Goal
        tk.Label(self.root, text="Daily Goal (liters)").grid(row=4, column=0, sticky=tk.W, padx=10, pady=5)
        self.daily_goal_entry = ttk.Entry(self.root)
        self.daily_goal_entry.insert(0, user_settings["daily_goal"])
        self.daily_goal_entry.grid(row=4, column=1, padx=10, pady=5)

        # Reminder Amount
        tk.Label(self.root, text="Reminder Amount (liters)").grid(row=5, column=0, sticky=tk.W, padx=10, pady=5)
        self.reminder_amount_entry = ttk.Entry(self.root)
        self.reminder_amount_entry.insert(0, user_settings["reminder_amount"])
        self.reminder_amount_entry.grid(row=5, column=1, padx=10, pady=5)

        # Start with Windows
        self.start_with_windows_var = tk.BooleanVar(value=user_settings["start_with_windows"])
        self.start_with_windows_check = ttk.Checkbutton(self.root, text="Start with Windows", variable=self.start_with_windows_var)
        self.start_with_windows_check.grid(row=6, column=0, columnspan=2, pady=5)

        # Water Drank Label
        self.water_drank_label = tk.Label(self.root, text=f"Water Drank: {self.total_water_drank} liters")
        self.water_drank_label.grid(row=7, column=0, columnspan=2, pady=5)

        # Remaining Label
        self.remaining_label = tk.Label(self.root, text="")
        self.remaining_label.grid(row=8, column=0, columnspan=2, pady=5)

        # Save Button
        self.save_button = ttk.Button(self.root, text="Save Settings", command=self.save_settings)
        self.save_button.grid(row=9, column=0, pady=10, padx=10, sticky=tk.EW)

        # Drink Water Button
        self.drink_water_button = ttk.Button(self.root, text="Drink Water", command=self.drink_water_action)
        self.drink_water_button.grid(row=9, column=1, padx=10, pady=10, sticky=tk.EW)

        # Clear Logs Button
        self.clear_logs_button = ttk.Button(self.root, text="Clear Logs", command=self.clear_logs_action)
        self.clear_logs_button.grid(row=9, column=2, padx=10, pady=10, sticky=tk.EW)

        # Log Messages
        tk.Label(self.root, text="Log Messages").grid(row=10, column=0, columnspan=3, sticky=tk.W, padx=10)
        self.log_text = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, width=60, height=10)
        self.log_text.grid(row=11, column=0, columnspan=3, padx=10, pady=5, sticky=tk.NSEW)

        # Social and GitHub icons with hyperlinks
        self.social_frame = tk.Frame(self.root)
        self.social_frame.grid(row=12, column=0, columnspan=3, pady=10)

        self.github_icon = tk.Label(self.social_frame, text="GitHub", fg="blue", cursor="hand2")
        self.github_icon.grid(row=0, column=0, padx=5)
        self.github_icon.bind("<Button-1>", lambda e: self.open_url("https://github.com/goenyan/WaterReminder"))

        self.twitter_icon = tk.Label(self.social_frame, text="Website", fg="blue", cursor="hand2")
        self.twitter_icon.grid(row=0, column=1, padx=5)
        self.twitter_icon.bind("<Button-1>", lambda e: self.open_url("https://mimiakane.com/"))

        self.linkedin_icon = tk.Label(self.social_frame, text="Genshin Wish Simulator", fg="blue", cursor="hand2")
        self.linkedin_icon.grid(row=0, column=2, padx=5)
        self.linkedin_icon.bind("<Button-1>", lambda e: self.open_url("https://giwish.mimiakane.com/"))
        
        self.linkedin_icon = tk.Label(self.social_frame, text="HSR Warp Simulator", fg="blue", cursor="hand2")
        self.linkedin_icon.grid(row=0, column=3, padx=5)
        self.linkedin_icon.bind("<Button-1>", lambda e: self.open_url("https://hsrwarp.mimiakane.com/"))

    def update_water_drank_label(self):
        self.water_drank_label.config(text=f"Water Drank: {self.total_water_drank} liters")

    def update_remaining_label(self):
        remaining = self.daily_goal - self.total_water_drank
        self.remaining_label.config(text=f"Remaining: {remaining} liters")

    def save_settings(self):
        user_settings["start_time"] = self.start_time_entry.get()
        user_settings["end_time"] = self.end_time_entry.get()
        user_settings["interval"] = int(self.interval_entry.get())
        user_settings["daily_goal"] = float(self.daily_goal_entry.get())
        user_settings["reminder_amount"] = float(self.reminder_amount_entry.get())
        user_settings["start_with_windows"] = self.start_with_windows_var.get()
        save_user_settings()
        messagebox.showinfo("Settings Saved", "Your settings have been saved.")

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

    def clear_logs_action(self):
        open(log_file, 'w').close()  # Clear the log file
        self.display_log_messages()

    def display_log_messages(self):
        self.log_text.delete('1.0', tk.END)
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                log_content = f.read()
                self.log_text.insert(tk.END, log_content)

    def schedule_initial_reminder(self):
        now = datetime.now()
        start_time = datetime.strptime(user_settings["start_time"], "%H:%M").time()
        end_time = datetime.strptime(user_settings["end_time"], "%H:%M").time()
        interval = timedelta(minutes=user_settings["interval"])

        # Calculate the next reminder time
        next_reminder_time = (now + interval).replace(second=0, microsecond=0)

        # Schedule the first reminder within the set period
        if start_time <= next_reminder_time.time() <= end_time:
            delay = (next_reminder_time - now).total_seconds()
            scheduler.enter(delay, 1, self.send_reminder)
            threading.Thread(target=run_scheduler, daemon=True).start()

    def send_reminder(self):
        start_time = datetime.strptime(user_settings["start_time"], "%H:%M").time()
        end_time = datetime.strptime(user_settings["end_time"], "%H:%M").time()
        interval = timedelta(minutes=user_settings["interval"])

        # Show the reminder message box
        self.show_reminder_messagebox()

        # Schedule the next reminder within the set period
        now = datetime.now()
        next_reminder_time = (now + interval).replace(second=0, microsecond=0)
        if start_time <= next_reminder_time.time() <= end_time:
            delay = (next_reminder_time - now).total_seconds()
            scheduler.enter(delay, 1, self.send_reminder)

    def show_reminder_messagebox(self):
        response = messagebox.showinfo("Water Reminder", "Time to drink water!")
        if response == 'ok':
            self.drink_water_action()

    def open_url(self, url):
        import webbrowser
        webbrowser.open_new(url)

def run_scheduler():
    scheduler.run()

if __name__ == "__main__":
    root = ttk.Window(themename="cosmo")
    app = WaterReminderApp(root)
    app.schedule_initial_reminder()
    root.mainloop()
