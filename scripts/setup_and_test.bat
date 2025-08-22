@echo off
echo ===============================================
echo  ROV Controller - Setup and Test (Windows)
echo ===============================================

REM switch to repo root (this .bat resides in scripts/)
cd /d "%~dp0.."

echo Using Python: %PYTHON%
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
  echo [ERROR] Python not found in PATH.
  echo Please install Python 3.8+ and ensure 'python' is available.
  pause
  exit /b 2
)

python scripts\setup_and_test.py
set EXITCODE=%ERRORLEVEL%
echo.
echo Done. Exit code: %EXITCODE%
pause
exit /b %EXITCODE%
