@echo off
pyinstaller --onefile --windowed ^
  --add-data "Icon.png;." ^
  --add-data "logo.png;." ^
  --add-data "Icon.ico;." ^
  --add-data "sound;sound" ^
  --add-data "locales;locales" ^
  --add-data "fonts;fonts" ^
  --icon=Icon.ico WaterReminderApp.py
pause