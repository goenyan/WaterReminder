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
import pystray
from pystray import MenuItem as item
import webbrowser

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

# HUD class
class WaterReminderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Water Reminder")

        # Add app icon
        self.root.iconphoto(False, tk.PhotoImage(file="Icon.png"))

        # Set minimum size
        self.root.minsize(500, 850)

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
        self.logo_image = self.logo_image.resize((300, 150), Image.LANCZOS)
        self.logo_photo = ImageTk.PhotoImage(self.logo_image)
        self.logo_label = tk.Label(root, image=self.logo_photo)
        self.logo_label.grid(row=0, column=0, padx=10, pady=10, columnspan=4)

        # Add Start Time
        self.start_time_label = ttk.Label(self.root, text="Start Time (HH:MM):")
        self.start_time_label.grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.start_time_entry = ttk.Entry(self.root)
        self.start_time_entry.grid(row=1, column=1, padx=5, pady=5)
        self.start_time_entry.insert(0, user_settings["start_time"])

        # Add End Time
        self.end_time_label = ttk.Label(self.root, text="End Time (HH:MM):")
        self.end_time_label.grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.end_time_entry = ttk.Entry(self.root)
        self.end_time_entry.grid(row=2, column=1, padx=5, pady=5)
        self.end_time_entry.insert(0, user_settings["end_time"])

        # Add Interval
        self.interval_label = ttk.Label(self.root, text="Interval (minutes):")
        self.interval_label.grid(row=3, column=0, padx=5, pady=5, sticky="e")
        self.interval_entry = ttk.Entry(self.root)
        self.interval_entry.grid(row=3, column=1, padx=5, pady=5)
        self.interval_entry.insert(0, user_settings["interval"])

        # Add Daily Goal
        self.daily_goal_label = ttk.Label(self.root, text="Daily Goal (liters):")
        self.daily_goal_label.grid(row=4, column=0, padx=5, pady=5, sticky="e")
        self.daily_goal_entry = ttk.Entry(self.root)
        self.daily_goal_entry.grid(row=4, column=1, padx=5, pady=5)
        self.daily_goal_entry.insert(0, user_settings["daily_goal"])

        # Add Reminder Amount
        self.reminder_amount_label = ttk.Label(self.root, text="Reminder Amount (liters):")
        self.reminder_amount_label.grid(row=5, column=0, padx=5, pady=5, sticky="e")
        self.reminder_amount_entry = ttk.Entry(self.root)
        self.reminder_amount_entry.grid(row=5, column=1, padx=5, pady=5)
        self.reminder_amount_entry.insert(0, user_settings["reminder_amount"])

        # Add Start with Windows checkbox
        self.start_with_windows_var = tk.BooleanVar()
        self.start_with_windows_check = ttk.Checkbutton(
            self.root, text="Start with Windows", variable=self.start_with_windows_var)
        self.start_with_windows_check.grid(
            row=6, column=0, columnspan=2, padx=5, pady=5)
        self.start_with_windows_var.set(user_settings["start_with_windows"])

        # Add Save Button
        self.save_button = ttk.Button(
            self.root, text="Save Settings", command=self.save_settings)
        self.save_button.grid(row=9, column=0, pady=10, padx=10, sticky=tk.EW)

        # Add "Drink Water" Button
        self.drink_water_button = ttk.Button(
            self.root, text="Drink Water", command=self.drink_water)
        self.drink_water_button.grid(row=9, column=1, padx=10, pady=10, sticky=tk.EW)

        # Add "Clear Log" Button
        self.clear_log_button = ttk.Button(
            self.root, text="Clear Log", command=self.clear_log)
        self.clear_log_button.grid(row=9, column=2, padx=10, pady=10, sticky=tk.EW)

        # Add Drank Amount Label
        self.drank_amount_label = ttk.Label(self.root, text="Drank Amount: 0.0 liters")
        self.drank_amount_label.grid(row=7, column=0, columnspan=2, pady=5)

        # Add Remaining Amount Label
        self.remaining_amount_label = ttk.Label(self.root, text="Remaining Amount: 2.0 liters")
        self.remaining_amount_label.grid(row=8, column=0, columnspan=2, pady=5)

        # Add Log View
        self.log_view_label = ttk.Label(self.root, text="Water Intake Log:")
        self.log_view_label.grid(row=10, column=0, columnspan=2, padx=5, pady=5)
        self.log_view = scrolledtext.ScrolledText(
            self.root, width=40, height=10, state='disabled')
        self.log_view.grid(row=11, column=0, columnspan=4, padx=5, pady=5)
        self.update_log_view()

        # Social and GitHub icons with hyperlinks
        self.social_frame = tk.Frame(self.root)
        self.social_frame.grid(row=12, column=0, columnspan=4, pady=10)

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

        self.create_tray_icon()

    def save_settings(self):
        user_settings["start_time"] = self.start_time_entry.get()
        user_settings["end_time"] = self.end_time_entry.get()
        user_settings["interval"] = int(self.interval_entry.get())
        user_settings["daily_goal"] = float(self.daily_goal_entry.get())
        user_settings["reminder_amount"] = float(self.reminder_amount_entry.get())
        user_settings["start_with_windows"] = self.start_with_windows_var.get()
        save_user_settings()
        self.schedule_reminders()
        messagebox.showinfo("Settings Saved", "Your settings have been saved.")

    def update_log_view(self):
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                log_content = f.read()
        else:
            log_content = ""
        self.log_view.configure(state='normal')
        self.log_view.delete(1.0, tk.END)
        self.log_view.insert(tk.INSERT, log_content)
        self.log_view.configure(state='disabled')

    def schedule_reminders(self):
        # Cancel all scheduled reminders first
        for event in scheduler.queue:
            scheduler.cancel(event)

        start_time = datetime.strptime(user_settings["start_time"], "%H:%M").time()
        end_time = datetime.strptime(user_settings["end_time"], "%H:%M").time()
        now = datetime.now()

        start_datetime = datetime.combine(now.date(), start_time)
        end_datetime = datetime.combine(now.date(), end_time)
        interval = timedelta(minutes=user_settings["interval"])

        current_time = now
        while current_time < end_datetime:
            if current_time > start_datetime:
                scheduler.enterabs(time.mktime(current_time.timetuple()), 1, self.show_reminder)
            current_time += interval

        threading.Thread(target=scheduler.run).start()

    def show_reminder(self):
        messagebox.showinfo("Water Reminder", "Time to drink water!")

    def create_tray_icon(self):
        icon_image = Image.open("Icon.png")
        menu = (item('Open', self.show_window), item('Quit', self.quit_app))
        self.tray_icon = pystray.Icon("WaterReminderApp", icon_image, "Water Reminder", menu)
        threading.Thread(target=self.tray_icon.run).start()

    def show_window(self, icon, item):
        self.root.deiconify()

    def quit_app(self, icon, item):
        self.tray_icon.stop()
        self.root.quit()

    def open_url(self, url):
        webbrowser.open(url)

    def hide_window(self):
        if messagebox.askyesno("Minimize to Tray", "Do you want to minimize to the system tray instead of closing?"):
            self.root.withdraw()
        else:
            self.quit_app(None, None)

    def drink_water(self):
        # Update drank amount and remaining amount labels
        current_drank = float(self.drank_amount_label.cget("text").split()[2])
        drank_amount = current_drank + user_settings["reminder_amount"]
        remaining_amount = user_settings["daily_goal"] - drank_amount

        # Update labels
        self.drank_amount_label.config(text=f"Drank Amount: {drank_amount:.2f} liters")
        self.remaining_amount_label.config(text=f"Remaining Amount: {remaining_amount:.2f} liters")

        # Log the water intake
        now = datetime.now()
        log_entry = f"{now.strftime('%Y-%m-%d %H:%M:%S')} - Drank {user_settings['reminder_amount']:.2f} liters\n"
        with open(log_file, "a") as f:
            f.write(log_entry)

        # Update log view
        self.update_log_view()

    def clear_log(self):
        # Clear the log file
        open(log_file, 'w').close()

        # Update log view
        self.update_log_view()
        messagebox.showinfo("Log Cleared", "Water intake log has been cleared.")

if __name__ == "__main__":
    root = ttk.Window(themename="cosmo")
    app = WaterReminderApp(root)
    root.protocol("WM_DELETE_WINDOW", app.hide_window)
    root.mainloop()
