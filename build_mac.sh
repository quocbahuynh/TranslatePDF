#!/bin/bash
# Default bash script to build the Mac App using PyInstaller

# Activate the virtual environment
source venv/bin/activate

# Build the app bundle
# Note: --add-data path separators on macOS/Linux use ':'
pyinstaller --noconfirm --onedir --windowed --add-data "NotoSans-Regular.ttf:." "main.py"
