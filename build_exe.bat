@echo off
REM Build script for Periodica App
REM Creates an executable using PyInstaller

echo Building Periodica App executable...

REM Install PyInstaller if not present
python -m pip install pyinstaller

REM Build the executable
python -m PyInstaller periodica-app.spec

echo.
echo Build complete! Executable is in dist\PeridicaApp\
echo.
pause
