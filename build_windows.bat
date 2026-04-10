@echo off
REM Default batch script to build the Windows executable using PyInstaller

REM Activate the virtual environment
call venv\Scripts\activate.bat

REM Build the executable
REM Note: --add-data path separators on Windows use ';'
pyinstaller --noconfirm --onedir --windowed --add-data "NotoSans-Regular.ttf;." "main.py"
