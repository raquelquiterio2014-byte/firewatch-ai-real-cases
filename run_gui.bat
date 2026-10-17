@echo off
cd /d "%~dp0"
py -3.12 main.py
if errorlevel 1 (
  echo.
  echo Launch failed. Install Python 3.12 with Tcl/Tk or run main.py in PyCharm.
  pause
)
