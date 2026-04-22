@echo off
pyinstaller --onefile --windowed ^
  --add-data "Icon.png;." ^
  --add-data "logo.png;." ^
  --icon=Icon.ico WaterReminderApp.py
pause