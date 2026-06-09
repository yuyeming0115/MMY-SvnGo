@echo off
chcp 65001 >nul 2>&1
echo.
echo ============================================================
echo   MMY SvnGo - One-Click Build
echo ============================================================
echo.

cd /d "%~dp0"

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

echo [1/2] Installing dependencies...
python -m pip install -r requirements.txt --quiet

echo [2/2] Building...
echo.
python build.py %*

echo.
echo ============================================================
echo   Build complete! Check release\ folder
echo ============================================================
echo.
pause
