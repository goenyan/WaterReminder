import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
from datetime import datetime, timedelta, date
import threading
import os
import sys
import json
import webbrowser
import tkinter.font as tkfont
from pathlib import Path

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk

import pystray
from pystray import MenuItem as item

import pygame

IS_WINDOWS = sys.platform.startswith("win")

try:
    import winshell
    from win32com.client import Dispatch
    HAVE_WIN_STARTUP = True
except Exception:
    HAVE_WIN_STARTUP = False

try:
    from win10toast import ToastNotifier
    HAVE_WIN_TOAST = True
except Exception:
    HAVE_WIN_TOAST = False

try:
    from plyer import notification as plyer_notification
    HAVE_PLYER = True
except Exception:
    HAVE_PLYER = False

def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()
SOUND_DIR = os.path.join(BASE_DIR, "sounds")
os.makedirs(SOUND_DIR, exist_ok=True)

log_file = os.path.join(BASE_DIR, "water_intake_log.txt")
settings_file = os.path.join(BASE_DIR, "settings.json")

pygame.mixer.init()

default_settings = {
    "start_time": "08:00",
    "end_time": "20:00",
    "interval": 60,
    "daily_goal": 2.0,
    "reminder_amount": 0.25,
    "start_with_windows": False,
    "sound_file": "cute-gugu-gaga.mp3",
    "sound_volume": 0.8,
    "theme": "cosmo",
    "default_language": "en-US",
}

if os.path.exists(settings_file):
    try:
        with open(settings_file, "r") as f:
            user_settings = json.load(f)
    except (json.JSONDecodeError, OSError):
        user_settings = default_settings.copy()
else:
    user_settings = default_settings.copy()

for k, v in default_settings.items():
    user_settings.setdefault(k, v)

def save_user_settings():
    with open(settings_file, "w") as f:
        json.dump(user_settings, f, indent=2)

LOCALES_DIR = os.path.join(BASE_DIR, "locales")
current_lang = user_settings.get("default_language", "en-US")
translations = {}

DEFAULT_EN = {
    "language": "Language",
    "start_time": "Start Time (HH:MM)",
    "end_time": "End Time (HH:MM)",
    "interval": "Reminder Interval (minutes)",
    "daily_goal": "Daily Goal (liters)",
    "reminder_amount": "Amount per Drink (liters)",
    "alert_sound": "Alert Sound",
    "browse_sound": "Browse...",
    "test_sound": "Test",
    "volume": "Volume",
    "start_with_windows": "Start with Windows",
    "theme": "Dark Mode",
    "water_drank": "Drank today: {amount:.2f} L",
    "remaining": "Remaining: {amount:.2f} L",
    "next_reminder_in": "Next reminder in {mm}:{ss}",
    "next_reminder_in_raw": "Next reminder in {value}",
    "save_settings": "Save Settings",
    "drink_water": "+ Custom Amount",
    "clear_logs": "Clear Logs",
    "undo_last": "Undo Last",
    "log_messages": "Log",
    "github": "GitHub",
    "website": "Website",
    "giwish": "Genshin Wish",
    "hsr": "HSR Warp",
    "log_drink": "[{time}] Drank {amount:.2f} L",
    "tab_home": "Home",
    "tab_history": "History",
    "tab_settings": "Settings",
    "history_title": "Last 7 Days",
    "history_avg": "7-day average: {amount:.2f} L",
    "history_best": "Best day: {amount:.2f} L",
    "history_streak": "Goal-met streak: {days} day(s)",
    "quick_add": "Quick add",
    "goal_reached": "Goal reached! Great job staying hydrated!",
    "settings_saved_title": "Settings Saved",
    "settings_saved_body": "Your settings have been saved.",
    "invalid_input_title": "Invalid Input",
    "invalid_time": "Please enter times in 24-hour HH:MM format (e.g. 08:00).",
    "invalid_number": "Please enter a valid positive number.",
    "invalid_end_after_start": "End time must be after start time.",
    "nothing_to_undo": "There is no drink logged today to undo.",
}

LANG_FILES = {
    "en-US": "en-US.json",
    "ja-JP": "ja-JP.json",
    "vi-VN": "vi-VN.json",
    "zh-CN": "zh-CN.json",
    "zh-TW": "zh-TW.json",
    "ph-PH": "ph-PH.json",
    "id-ID": "id-ID.json",
    "ko-KR": "ko-KR.json",
}

DISPLAY_TO_CODE = {
    "English": "en-US",
    "日本語": "ja-JP",
    "Tiếng Việt": "vi-VN",
    "简体中文": "zh-CN",
    "繁體中文": "zh-TW",
    "Bahasa Indonesia": "id-ID",
    "Filipino": "ph-PH",
    "한국어": "ko-KR",
}
CODE_TO_DISPLAY = {v: k for k, v in DISPLAY_TO_CODE.items()}

def load_language(lang_code):
    global current_lang, translations
    lang_file = os.path.join(LOCALES_DIR, f"{lang_code}.json")
    loaded = {}
    if os.path.exists(lang_file):
        try:
            with open(lang_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
        except (json.JSONDecodeError, OSError):
            loaded = {}
    else:
        lang_code = "en-US"

    merged = DEFAULT_EN.copy()
    merged.update(loaded)
    translations = merged
    current_lang = lang_code

def _(key, **kwargs):
    text = translations.get(key, DEFAULT_EN.get(key, key))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return text

load_language(user_settings.get("default_language", "en-US"))

def make_white_variant(img, threshold=90, protect_box=(0.684, 0.218, 0.958, 0.784)):
    img = img.convert("RGBA")
    w, h = img.size
    px0 = int(w * protect_box[0])
    py0 = int(h * protect_box[1])
    px1 = int(w * protect_box[2])
    py1 = int(h * protect_box[3])
    pixels = list(img.getdata())
    new_pixels = []
    for i, (r, g, b, a) in enumerate(pixels):
        x = i % w
        y = i // w
        protected = (px0 <= x < px1) and (py0 <= y < py1)
        if a == 0 or protected:
            new_pixels.append((r, g, b, a))
            continue
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        if luminance < threshold:
            new_pixels.append((255, 255, 255, a))
        else:
            new_pixels.append((r, g, b, a))
    out = Image.new("RGBA", img.size)
    out.putdata(new_pixels)
    return out


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def add_to_startup():
    if not HAVE_WIN_STARTUP:
        return
    startup = winshell.startup()
    exe_path = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)
    shortcut_path = os.path.join(startup, "WaterReminder.lnk")
    shell = Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.Targetpath = exe_path
    shortcut.WorkingDirectory = os.path.dirname(exe_path)
    shortcut.IconLocation = exe_path
    shortcut.save()

def remove_from_startup():
    if not HAVE_WIN_STARTUP:
        return
    startup = winshell.startup()
    shortcut_path = os.path.join(startup, "WaterReminder.lnk")
    if os.path.exists(shortcut_path):
        os.remove(shortcut_path)

def read_log_entries():
    entries = []
    if not os.path.exists(log_file):
        return entries
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries

def write_log_entries(entries):
    with open(log_file, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

def total_for_date(entries, target_date):
    total = 0.0
    for e in entries:
        if e.get("type") != "drink":
            continue
        ts = e.get("timestamp", "")
        try:
            d = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").date()
        except ValueError:
            continue
        if d == target_date:
            total += float(e.get("amount", 0))
    return total

def history_last_n_days(entries, n=7):
    today = date.today()
    days = [today - timedelta(days=i) for i in range(n - 1, -1, -1)]
    return [(d, total_for_date(entries, d)) for d in days]

class WaterReminderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Water Reminder")

        self.root.iconphoto(False, tk.PhotoImage(file=resource_path("Icon.png")))

        window_width, window_height = 520, 760
        self.root.minsize(480, 680)
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        entries = read_log_entries()
        self.today = date.today()

        self.total_water_drank = total_for_date(entries, self.today)
        self.daily_goal = user_settings["daily_goal"]
        self.next_reminder_time = None
        self.last_drink_time = datetime.now()
        self._goal_notified_today = self.total_water_drank >= self.daily_goal

        self.create_widgets()
        self.refresh_all_labels()
        self.display_log_messages()
        self.refresh_history_tab()
        self.apply_widget_theme_colors()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.tray_icon = pystray.Icon("WaterReminderApp")
        self.tray_image = Image.open(resource_path("Icon.png"))
        self.tray_icon.icon = self.tray_image
        self.tray_icon.menu = pystray.Menu(
            item('Drink Water', self.tray_drink_water),
            item('Open', self.show_window),
            item('Quit', self.on_closing_tray),
        )

        self.notifier = ToastNotifier() if HAVE_WIN_TOAST else None

        self.schedule_initial_reminder()

        self.root.after(60_000, self.check_day_rollover)

    def create_widgets(self):
        style = ttk.Style()
        button_font = tkfont.Font(family="Noto Sans", size=9)
        style.configure("Big.TButton", padding=(12, 4, 12, 8), font=button_font)
        style.configure("Quick.TButton", padding=(8, 4), font=button_font)

        self.logo_image = Image.open(resource_path("logo.png"))
        self.logo_image = self.logo_image.resize((260, 130), Image.Resampling.LANCZOS)
        self.logo_photo_light = ImageTk.PhotoImage(self.logo_image)
        self.logo_photo_dark = ImageTk.PhotoImage(make_white_variant(self.logo_image))
        initial_logo = self.logo_photo_dark if user_settings.get("theme") == "darkly" else self.logo_photo_light
        self.logo_label = tk.Label(self.root, image=initial_logo)
        self.logo_label.image = initial_logo
        self.logo_label.pack(pady=(10, 0))

        self.top_bar = tk.Frame(self.root)
        self.top_bar.pack(fill=tk.X, padx=10, pady=(6, 0))

        self.language_label = tk.Label(self.top_bar, text=_("language"))
        self.language_label.pack(side=tk.LEFT)

        current_code = user_settings.get("default_language", "en-US")
        current_display = CODE_TO_DISPLAY.get(current_code, "English")
        self.language_display_var = tk.StringVar(value=current_display)
        self.language_combo = ttk.Combobox(
            self.top_bar,
            textvariable=self.language_display_var,
            values=list(DISPLAY_TO_CODE.keys()),
            state="readonly",
            width=14,
        )
        self.language_combo.pack(side=tk.LEFT, padx=8)
        self.language_combo.bind("<<ComboboxSelected>>", self.on_language_changed)

        self.theme_var = tk.BooleanVar(value=(user_settings.get("theme") == "darkly"))
        self.theme_check = ttk.Checkbutton(
            self.top_bar, text=_("theme"), variable=self.theme_var,
            command=self.on_theme_toggle, bootstyle="round-toggle"
        )
        self.theme_check.pack(side=tk.RIGHT)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.home_tab = tk.Frame(self.notebook)
        self.history_tab = tk.Frame(self.notebook)
        self.settings_tab = tk.Frame(self.notebook)
        self.notebook.add(self.home_tab, text=_("tab_home"))
        self.notebook.add(self.history_tab, text=_("tab_history"))
        self.notebook.add(self.settings_tab, text=_("tab_settings"))

        self.build_home_tab()
        self.build_history_tab()
        self.build_settings_tab()

        self.social_frame = tk.Frame(self.root)
        self.social_frame.pack(pady=(0, 10))
        self.github_icon = self._link_label(self.social_frame, _("github"),
                                             "https://github.com/goenyan/WaterReminder")
        self.website_icon = self._link_label(self.social_frame, _("website"), "https://mimiakane.com/")
        self.giwish_icon = self._link_label(self.social_frame, _("giwish"), "https://giwish.mimiakane.com/")
        self.hsr_icon = self._link_label(self.social_frame, _("hsr"), "https://hsrwarp.mimiakane.com/")
        for i, lbl in enumerate((self.github_icon, self.website_icon, self.giwish_icon, self.hsr_icon)):
            lbl.grid(row=0, column=i, padx=6)

    def _link_label(self, parent, text, url):
        lbl = tk.Label(parent, text=text, fg="#2f7de1", cursor="hand2")
        lbl.bind("<Button-1>", lambda e: self.open_url(url))
        return lbl

    def build_home_tab(self):
        f = self.home_tab

        self.water_drank_label = tk.Label(f, font=("Noto Sans", 13, "bold"))
        self.water_drank_label.pack(pady=(12, 2))

        self.remaining_label = tk.Label(f, font=("Noto Sans", 10))
        self.remaining_label.pack(pady=(0, 8))

        self.progress_bar = ttk.Progressbar(
            f, orient="horizontal", mode="determinate", length=400,
            bootstyle="success-striped"
        )
        self.progress_bar.pack(padx=20, pady=(0, 10), fill=tk.X)

        self.countdown_label = tk.Label(f, font=("Noto Sans", 10))
        self.countdown_label.pack(pady=(0, 12))

        self.quick_frame = tk.LabelFrame(f, text=_("quick_add"), padx=10, pady=8)
        self.quick_frame.pack(padx=20, pady=(0, 10), fill=tk.X)
        for amount in (0.1, 0.25, 0.5):
            b = ttk.Button(
                self.quick_frame, text=f"+{int(amount * 1000)} ml",
                style="Quick.TButton", bootstyle="info-outline",
                command=lambda a=amount: self.drink_water_action(a)
            )
            b.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)

        self.action_frame = tk.Frame(f)
        self.action_frame.pack(padx=20, pady=(0, 10), fill=tk.X)
        self.drink_water_button = ttk.Button(
            self.action_frame, text=_("drink_water"), style="Big.TButton",
            bootstyle="success",
            command=lambda: self.drink_water_action(None)
        )
        self.drink_water_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 4))

        self.undo_button = ttk.Button(
            self.action_frame, text=_("undo_last"), style="Big.TButton",
            bootstyle="secondary-outline",
            command=self.undo_last_drink
        )
        self.undo_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(4, 0))

        self.clear_logs_button = ttk.Button(
            f, text=_("clear_logs"), style="Big.TButton", bootstyle="danger-outline",
            command=self.clear_logs_action
        )
        self.clear_logs_button.pack(padx=20, pady=(0, 10), fill=tk.X)

        self.log_label = tk.Label(f, text=_("log_messages"), anchor="w")
        self.log_label.pack(padx=20, fill=tk.X)

        self.log_text = scrolledtext.ScrolledText(f, wrap=tk.WORD, height=8)
        self.log_text.pack(padx=20, pady=(2, 12), fill=tk.BOTH, expand=True)

    def build_history_tab(self):
        f = self.history_tab
        self.history_title_label = tk.Label(f, text=_("history_title"), font=("Noto Sans", 12, "bold"))
        self.history_title_label.pack(pady=(16, 6))

        self.history_canvas = tk.Canvas(f, width=440, height=220, highlightthickness=0)
        self.history_canvas.pack(pady=10)

        self.history_avg_label = tk.Label(f, font=("Noto Sans", 10))
        self.history_avg_label.pack(pady=2)
        self.history_best_label = tk.Label(f, font=("Noto Sans", 10))
        self.history_best_label.pack(pady=2)
        self.history_streak_label = tk.Label(f, font=("Noto Sans", 10))
        self.history_streak_label.pack(pady=2)

    def refresh_history_tab(self):
        entries = read_log_entries()
        data = history_last_n_days(entries, 7)
        goal = user_settings["daily_goal"]

        canvas = self.history_canvas
        canvas.delete("all")
        w, h = 440, 220
        pad_bottom = 30
        pad_top = 10
        chart_h = h - pad_bottom - pad_top
        bar_w = 40
        gap = (w - bar_w * len(data)) / (len(data) + 1)

        max_val = max([v for _, v in data] + [goal, 0.1])

        goal_y = pad_top + chart_h - (goal / max_val) * chart_h
        canvas.create_line(0, goal_y, w, goal_y, dash=(4, 2), fill="#e0725a")
        canvas.create_text(w - 4, goal_y - 8, text="goal", anchor="e", fill="#e0725a", font=("Noto Sans", 8))

        x = gap
        for d, val in data:
            bar_h = (val / max_val) * chart_h if max_val > 0 else 0
            y0 = pad_top + chart_h - bar_h
            color = "#3aa757" if val >= goal else "#5aa9e6"
            canvas.create_rectangle(x, y0, x + bar_w, pad_top + chart_h, fill=color, outline="")
            canvas.create_text(x + bar_w / 2, pad_top + chart_h + 12, text=d.strftime("%a"),
                                font=("Noto Sans", 8))
            canvas.create_text(x + bar_w / 2, y0 - 8, text=f"{val:.1f}", font=("Noto Sans", 8))
            x += bar_w + gap

        totals = [v for _, v in data]
        avg = sum(totals) / len(totals) if totals else 0.0
        best = max(totals) if totals else 0.0
        streak = 0
        for _day, v in reversed(data):
            if v >= goal and goal > 0:
                streak += 1
            else:
                break

        self.history_avg_label.config(text=_("history_avg", amount=avg))
        self.history_best_label.config(text=_("history_best", amount=best))
        self.history_streak_label.config(text=_("history_streak", days=streak))

    def build_settings_tab(self):
        f = self.settings_tab
        for c in range(3):
            f.grid_columnconfigure(c, weight=1)

        row = 0
        self.start_time_label = tk.Label(f, text=_("start_time"))
        self.start_time_label.grid(row=row, column=0, sticky=tk.W, padx=10, pady=6)
        self.start_time_entry = ttk.Entry(f)
        self.start_time_entry.insert(0, user_settings["start_time"])
        self.start_time_entry.grid(row=row, column=1, padx=10, pady=6, sticky=tk.EW)

        row += 1
        self.end_time_label = tk.Label(f, text=_("end_time"))
        self.end_time_label.grid(row=row, column=0, sticky=tk.W, padx=10, pady=6)
        self.end_time_entry = ttk.Entry(f)
        self.end_time_entry.insert(0, user_settings["end_time"])
        self.end_time_entry.grid(row=row, column=1, padx=10, pady=6, sticky=tk.EW)

        row += 1
        self.interval_label = tk.Label(f, text=_("interval"))
        self.interval_label.grid(row=row, column=0, sticky=tk.W, padx=10, pady=6)
        self.interval_entry = ttk.Entry(f)
        self.interval_entry.insert(0, user_settings["interval"])
        self.interval_entry.grid(row=row, column=1, padx=10, pady=6, sticky=tk.EW)

        row += 1
        self.daily_goal_label = tk.Label(f, text=_("daily_goal"))
        self.daily_goal_label.grid(row=row, column=0, sticky=tk.W, padx=10, pady=6)
        self.daily_goal_entry = ttk.Entry(f)
        self.daily_goal_entry.insert(0, user_settings["daily_goal"])
        self.daily_goal_entry.grid(row=row, column=1, padx=10, pady=6, sticky=tk.EW)

        row += 1
        self.reminder_amount_label = tk.Label(f, text=_("reminder_amount"))
        self.reminder_amount_label.grid(row=row, column=0, sticky=tk.W, padx=10, pady=6)
        self.reminder_amount_entry = ttk.Entry(f)
        self.reminder_amount_entry.insert(0, user_settings["reminder_amount"])
        self.reminder_amount_entry.grid(row=row, column=1, padx=10, pady=6, sticky=tk.EW)

        row += 1
        self.alert_sound_label = tk.Label(f, text=_("alert_sound"))
        self.alert_sound_label.grid(row=row, column=0, sticky=tk.W, padx=10, pady=6)
        self.sound_label = tk.Label(f, text=user_settings["sound_file"] or "Default / None")
        self.sound_label.grid(row=row, column=1, padx=10, pady=6, sticky=tk.W)
        self.sound_btns = tk.Frame(f)
        self.sound_btns.grid(row=row, column=2, padx=10, pady=6, sticky=tk.EW)
        self.browse_sound_button = ttk.Button(
            self.sound_btns, text=_("browse_sound"), command=self.choose_sound_file,
            style="Big.TButton", bootstyle="secondary"
        )
        self.browse_sound_button.pack(side=tk.LEFT, padx=(0, 4))
        self.test_sound_button = ttk.Button(
            self.sound_btns, text=_("test_sound"), command=self.play_alert_sound,
            style="Big.TButton", bootstyle="secondary-outline"
        )
        self.test_sound_button.pack(side=tk.LEFT)

        row += 1
        self.volume_label = tk.Label(f, text=_("volume"))
        self.volume_label.grid(row=row, column=0, sticky=tk.W, padx=10, pady=6)
        self.volume_var = tk.DoubleVar(value=user_settings.get("sound_volume", 0.8))
        self.volume_scale = ttk.Scale(
            f, from_=0.0, to=1.0, variable=self.volume_var, orient=tk.HORIZONTAL,
            command=self.on_volume_changed
        )
        self.volume_scale.grid(row=row, column=1, padx=10, pady=6, sticky=tk.EW)

        row += 1
        self.start_with_windows_var = tk.BooleanVar(value=user_settings["start_with_windows"])
        self.start_with_windows_check = ttk.Checkbutton(
            f, variable=self.start_with_windows_var, bootstyle="round-toggle"
        )
        self.start_with_windows_check.grid(row=row, column=0, padx=10, pady=6, sticky=tk.E)
        self.start_with_windows_label = tk.Label(f, text=_("start_with_windows"))
        self.start_with_windows_label.grid(row=row, column=1, padx=5, pady=6, sticky=tk.W)
        if not HAVE_WIN_STARTUP:
            self.start_with_windows_check.config(state="disabled")
            self.start_with_windows_label.config(
                text=_("start_with_windows") + "  (Windows only)"
            )

        row += 1
        self.save_button = ttk.Button(
            f, text=_("save_settings"), command=self.save_settings,
            style="Big.TButton", bootstyle="success"
        )
        self.save_button.grid(row=row, column=0, columnspan=3, pady=16, padx=10, sticky=tk.EW)

    def refresh_all_labels(self):
        self.water_drank_label.config(text=_("water_drank", amount=self.total_water_drank))
        remaining = max(0.0, self.daily_goal - self.total_water_drank)
        self.remaining_label.config(text=_("remaining", amount=remaining))
        pct = 0 if self.daily_goal <= 0 else min(100, (self.total_water_drank / self.daily_goal) * 100)
        self.progress_bar["value"] = pct

    def show_info_dialog(self, title, body):
        style = ttk.Style()
        bg = style.colors.bg
        fg = style.colors.fg
        dialog = tk.Toplevel(self.root)
        dialog.configure(background=bg)
        dialog.title(title)
        try:
            dialog.iconphoto(False, tk.PhotoImage(file=resource_path("Icon.png")))
        except Exception:
            pass
        dialog.resizable(False, False)
        dialog.grab_set()
        tk.Label(
            dialog, text=body, padx=20, pady=15, wraplength=280, justify="left",
            background=bg, foreground=fg,
        ).pack()

        def close_dialog():
            if dialog.winfo_exists():
                dialog.destroy()

        ttk.Button(dialog, text="OK", command=close_dialog, bootstyle="success").pack(pady=(0, 15))
        dialog.update_idletasks()
        w, h = dialog.winfo_width(), dialog.winfo_height()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (w // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (h // 2)
        dialog.geometry(f"{w}x{h}+{x}+{y}")
        dialog.after(3000, close_dialog)

    def on_language_changed(self, event=None):
        display_name = self.language_display_var.get()
        new_lang = DISPLAY_TO_CODE.get(display_name, "en-US")
        user_settings["default_language"] = new_lang
        save_user_settings()
        load_language(new_lang)
        self.update_ui_language()

    def apply_widget_theme_colors(self):
        style = ttk.Style()
        colors = style.colors
        bg = colors.bg
        fg = colors.fg
        input_bg = colors.inputbg
        input_fg = colors.inputfg

        self.root.configure(background=bg)

        frames = [
            self.top_bar, self.home_tab, self.history_tab, self.settings_tab,
            self.social_frame, self.quick_frame, self.action_frame, self.sound_btns,
        ]
        for frame in frames:
            frame.configure(background=bg)
        self.quick_frame.configure(foreground=fg)

        self.logo_label.configure(background=bg)

        labels = [
            self.language_label, self.water_drank_label, self.remaining_label,
            self.countdown_label, self.log_label, self.history_title_label,
            self.history_avg_label, self.history_best_label, self.history_streak_label,
            self.start_time_label, self.end_time_label, self.interval_label,
            self.daily_goal_label, self.reminder_amount_label, self.alert_sound_label,
            self.sound_label, self.volume_label, self.start_with_windows_label,
        ]
        for label in labels:
            label.configure(background=bg, foreground=fg)

        for link in (self.github_icon, self.website_icon, self.giwish_icon, self.hsr_icon):
            link.configure(background=bg)

        self.log_text.configure(background=input_bg, foreground=input_fg, insertbackground=fg)
        self.history_canvas.configure(background=bg)

    def on_theme_toggle(self):
        theme = "darkly" if self.theme_var.get() else "cosmo"
        user_settings["theme"] = theme
        save_user_settings()
        try:
            ttk.Style().theme_use(theme)
        except Exception:
            pass
        logo_photo = self.logo_photo_dark if theme == "darkly" else self.logo_photo_light
        self.logo_label.config(image=logo_photo)
        self.logo_label.image = logo_photo
        self.apply_widget_theme_colors()

    def on_volume_changed(self, value):
        user_settings["sound_volume"] = float(value)

    def update_ui_language(self):
        self.language_label.config(text=_("language"))
        self.theme_check.config(text=_("theme"))
        self.start_time_label.config(text=_("start_time"))
        self.end_time_label.config(text=_("end_time"))
        self.interval_label.config(text=_("interval"))
        self.daily_goal_label.config(text=_("daily_goal"))
        self.reminder_amount_label.config(text=_("reminder_amount"))
        self.alert_sound_label.config(text=_("alert_sound"))
        self.browse_sound_button.config(text=_("browse_sound"))
        self.test_sound_button.config(text=_("test_sound"))
        self.volume_label.config(text=_("volume"))
        if HAVE_WIN_STARTUP:
            self.start_with_windows_label.config(text=_("start_with_windows"))
        self.log_label.config(text=_("log_messages"))
        self.github_icon.config(text=_("github"))
        self.website_icon.config(text=_("website"))
        self.giwish_icon.config(text=_("giwish"))
        self.hsr_icon.config(text=_("hsr"))
        self.save_button.config(text=_("save_settings"))
        self.drink_water_button.config(text=_("drink_water"))
        self.clear_logs_button.config(text=_("clear_logs"))
        self.undo_button.config(text=_("undo_last"))
        self.history_title_label.config(text=_("history_title"))
        self.notebook.tab(self.home_tab, text=_("tab_home"))
        self.notebook.tab(self.history_tab, text=_("tab_history"))
        self.notebook.tab(self.settings_tab, text=_("tab_settings"))
        self.refresh_all_labels()
        self.display_log_messages()
        self.refresh_history_tab()

    @staticmethod
    def _parse_hhmm(value):
        return datetime.strptime(value.strip(), "%H:%M").time()

    def save_settings(self):
        try:
            start_time = self._parse_hhmm(self.start_time_entry.get())
            end_time = self._parse_hhmm(self.end_time_entry.get())
        except ValueError:
            messagebox.showerror(_("invalid_input_title"), _("invalid_time"))
            return

        if end_time <= start_time:
            messagebox.showerror(_("invalid_input_title"), _("invalid_end_after_start"))
            return

        try:
            interval = int(self.interval_entry.get())
            daily_goal = float(self.daily_goal_entry.get())
            reminder_amount = float(self.reminder_amount_entry.get())
            if interval <= 0 or daily_goal <= 0 or reminder_amount <= 0:
                raise ValueError
        except (TypeError, ValueError):
            messagebox.showerror(_("invalid_input_title"), _("invalid_number"))
            return

        user_settings["start_time"] = self.start_time_entry.get().strip()
        user_settings["end_time"] = self.end_time_entry.get().strip()
        user_settings["interval"] = max(1, interval)
        user_settings["daily_goal"] = daily_goal
        user_settings["reminder_amount"] = reminder_amount
        user_settings["start_with_windows"] = self.start_with_windows_var.get()
        user_settings["sound_volume"] = float(self.volume_var.get())
        save_user_settings()

        self.daily_goal = daily_goal
        self.refresh_all_labels()
        self.refresh_history_tab()
        self.show_info_dialog(_("settings_saved_title"), _("settings_saved_body"))

        if HAVE_WIN_STARTUP:
            if user_settings["start_with_windows"]:
                add_to_startup()
            else:
                remove_from_startup()

        self.reset_timer_from_now()

    def _log_drink(self, amount):
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "drink",
            "amount": amount,
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def drink_water_action(self, amount):
        if amount is None:
            try:
                amount = float(self.reminder_amount_entry.get())
                if amount <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                messagebox.showerror(_("invalid_input_title"), _("invalid_number"))
                return

        self.total_water_drank += amount
        self._log_drink(amount)
        self.refresh_all_labels()
        self.display_log_messages()
        self.refresh_history_tab()
        self.reset_timer_from_now()

        if self.total_water_drank >= self.daily_goal and not self._goal_notified_today:
            self._goal_notified_today = True
            self.show_info_dialog(_("settings_saved_title").replace("Saved", "") or "Water Reminder",
                                   _("goal_reached"))

    def tray_drink_water(self, icon, menu_item):
        self.root.after(0, lambda: self.drink_water_action(None))

    def undo_last_drink(self):
        entries = read_log_entries()
        today = date.today()
        for i in range(len(entries) - 1, -1, -1):
            e = entries[i]
            if e.get("type") != "drink":
                continue
            ts = e.get("timestamp", "")
            try:
                d = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").date()
            except ValueError:
                continue
            if d == today:
                removed = entries.pop(i)
                write_log_entries(entries)
                self.total_water_drank = max(0.0, self.total_water_drank - float(removed.get("amount", 0)))
                self.refresh_all_labels()
                self.display_log_messages()
                self.refresh_history_tab()
                return
        messagebox.showinfo(_("invalid_input_title").replace("Invalid Input", "Water Reminder"),
                             _("nothing_to_undo"))

    def clear_logs_action(self):
        if not messagebox.askyesno("Water Reminder", "Clear all logged history? This cannot be undone."):
            return
        open(log_file, 'w').close()
        self.total_water_drank = 0.0
        self.refresh_all_labels()
        self.display_log_messages()
        self.refresh_history_tab()

    def display_log_messages(self):
        self.log_text.delete('1.0', tk.END)
        lines_out = []
        for entry in read_log_entries():
            if entry.get("type") == "drink":
                ts = entry.get("timestamp", "")
                amount = entry.get("amount", 0)
                lines_out.append(_("log_drink", time=ts, amount=amount))
        if lines_out:
            self.log_text.insert(tk.END, "\n".join(lines_out) + "\n")

    def schedule_initial_reminder(self):
        self.reset_timer_from_now()
        self.update_countdown_label()

    def reset_timer_from_now(self):
        self.last_drink_time = datetime.now()
        try:
            start_time = self._parse_hhmm(user_settings["start_time"])
            end_time = self._parse_hhmm(user_settings["end_time"])
        except ValueError:
            start_time, end_time = self._parse_hhmm("08:00"), self._parse_hhmm("20:00")
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
        self.countdown_label.config(text=_("next_reminder_in", mm=f"{minutes:02d}", ss=f"{seconds:02d}"))
        self.root.after(1000, self.update_countdown_label)

    def check_day_rollover(self):
        if date.today() != self.today:
            self.today = date.today()
            self.total_water_drank = 0.0
            self._goal_notified_today = False
            self.refresh_all_labels()
            self.refresh_history_tab()
        self.root.after(60_000, self.check_day_rollover)

    def send_reminder(self):
        try:
            start_time = self._parse_hhmm(user_settings["start_time"])
            end_time = self._parse_hhmm(user_settings["end_time"])
        except ValueError:
            start_time, end_time = self._parse_hhmm("08:00"), self._parse_hhmm("20:00")

        self.show_reminder_notification()

        now = datetime.now()
        interval_minutes = max(1, int(user_settings["interval"]))
        interval = timedelta(minutes=interval_minutes)
        next_reminder_time = (now + interval).replace(second=0, microsecond=0)
        if start_time <= next_reminder_time.time() <= end_time:
            self.next_reminder_time = next_reminder_time
        else:
            self.next_reminder_time = None

    def show_reminder_notification(self):
        title, body = "Water Reminder", "Time to drink water!"
        if HAVE_WIN_TOAST and self.notifier is not None:
            try:
                self.notifier.show_toast(title, body, icon_path=resource_path("Icon.ico"),
                                          duration=5, threaded=True)
            except Exception:
                pass
        elif HAVE_PLYER:
            try:
                plyer_notification.notify(title=title, message=body, timeout=5)
            except Exception:
                pass
        self.play_alert_sound()

    def play_alert_sound(self):
        def _play():
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
                        pygame.mixer.music.set_volume(float(user_settings.get("sound_volume", 0.8)))
                        pygame.mixer.music.play()
                        return
                    except Exception:
                        continue

        threading.Thread(target=_play, daemon=True).start()

    def open_url(self, url):
        webbrowser.open_new(url)

    def on_closing(self):
        if messagebox.askyesno("Minimize to tray", "Do you want to minimize the app to the system tray?"):
            self.hide_window()
        else:
            self.root.destroy()

    def hide_window(self):
        self.root.withdraw()
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_window(self, icon, menu_item):
        self.root.after(0, self.root.deiconify)
        icon.stop()

    def on_closing_tray(self, icon, menu_item):
        icon.stop()
        self.root.after(0, self.root.destroy)

    def choose_sound_file(self):
        file_path = filedialog.askopenfilename(
            title="Choose alert sound",
            initialdir=SOUND_DIR,
            filetypes=[("Audio files", "*.mp3 *.wav *.ogg"), ("All files", "*.*")],
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
                messagebox.showerror("Error", f"Could not copy sound file:\n{e}")
                return
        user_settings["sound_file"] = filename
        self.sound_label.config(text=filename)
        save_user_settings()

if __name__ == "__main__":
    root = ttk.Window(themename=user_settings.get("theme", "cosmo"))
    font_path = Path(BASE_DIR) / "fonts" / "NotoSans-Regular.ttf"
    default_font = tkfont.nametofont("TkDefaultFont")
    default_font.configure(family="Noto Sans", size=9)
    root.option_add("*Font", default_font)
    app = WaterReminderApp(root)
    root.mainloop()

