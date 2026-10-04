@echo off
REM periodica-app build pipeline (Windows). See README.md, "Development".
REM
REM   build.bat          ruff lint + tier-A tests (headless)
REM   build.bat gpu      ... then tier-B tests (needs a GPU / GL context)
REM   build.bat exe      ... then a PyInstaller one-folder build in dist\PeriodicaApp
REM   build.bat setup    pip install -e ".[dev]" first, then lint + tier-A tests
setlocal
cd /d "%~dp0"
REM Test the sources in this checkout even if another copy is installed.
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"
set "TARGET=%~1"
if not "%TARGET%"=="" if /I not "%TARGET%"=="gpu" if /I not "%TARGET%"=="exe" if /I not "%TARGET%"=="setup" (
    echo usage: build.bat [gpu^|exe^|setup]
    exit /b 2
)

if /I "%TARGET%"=="setup" (
    echo === pip install -e .[dev]
    python -m pip install -e ".[dev]" || goto :fail
)

echo === ruff
python -m ruff check src tests tools || goto :fail

echo === pytest, tier A - headless
python -m pytest tests -q || goto :fail

if /I "%TARGET%"=="gpu" (
    echo === pytest, tier B - gpu
    python -m pytest tests -q -m gpu || goto :fail
)

if /I "%TARGET%"=="exe" (
    echo === PyInstaller
    python -m PyInstaller --noconfirm periodica-app.spec || goto :fail
    echo Executable: dist\PeriodicaApp\PeriodicaApp.exe
)

echo === build OK
exit /b 0

:fail
echo === build FAILED
exit /b 1
