@echo off
pyinstaller --onefile --windowed ^
  --add-data "Icon.png;." ^
  --add-data "logo.png;." ^
  --add-data "Icon.ico;." ^
  --icon=Icon.ico WaterReminderApp.py
pause