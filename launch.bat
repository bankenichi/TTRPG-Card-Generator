@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
set "PYTHONNOUSERSITE=1"

echo ==============================================
echo Launching TTRPG Card Generator
echo ==============================================

set "PYTHON_DIR=%CD%\python-env"

:: Check install.lock — authoritative signal that install completed successfully
IF NOT EXIST "install.lock" (
    echo Install has not been completed. Please run install.bat first!
    pause
    exit /b 1
)

:: Check for standalone Python
IF NOT EXIST "%PYTHON_DIR%\python.exe" (
    echo Python environment is missing or broken. Please run install.bat again to repair.
    pause
    exit /b 1
)

:: Run the Launcher/Setup script
echo Starting Launcher...
"%PYTHON_DIR%\python.exe" launcher.py
pause
