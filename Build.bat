@echo off
pyinstaller --windowed ^
  --exclude-module numpy ^
  --add-data "Icon.png;." ^
  --add-data "logo.png;." ^
  --add-data "Icon.ico;." ^
  --add-data "locales;locales" ^
  --add-data "fonts;fonts" ^
  --add-data "sounds;sounds" ^
  --icon=Icon.ico WaterReminderApp.py
pause