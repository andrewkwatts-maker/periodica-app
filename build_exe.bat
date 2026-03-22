@echo off
REM Build script for Periodics application
REM Creates an executable using PyInstaller and copies required data files

echo Building Periodics executable...

REM Install PyInstaller if not present
python -m pip install pyinstaller

REM Build the executable using python -m
python -m PyInstaller --onedir --windowed --name Periodics ^
    --add-data "data;data" ^
    main.py

REM Copy additional config files to dist folder if they exist
if exist "constants.py" copy "constants.py" "dist\Periodics\"

echo.
echo Build complete! Executable is in dist\Periodics\
echo.
pause
