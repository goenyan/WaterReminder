@echo off
pyinstaller --onefile --windowed ^
  --add-data "Icon.png;." ^
  --add-data "logo.png;." ^
  --add-data "Icon.ico;." ^
  --add-data "sound;sound" ^
  --icon=Icon.ico WaterReminderApp.py
pause