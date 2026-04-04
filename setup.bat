@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo   Inventory / Sales Tool - Setup
echo ========================================
echo.
echo Creates .venv and installs requirements.txt
echo (First run may take a few minutes.)
echo.

where python >nul 2>nul
if %errorlevel%==0 (
  set "PYTHON=python"
) else (
  where py >nul 2>nul
  if %errorlevel%==0 (
    rem Prefer latest Python 3.x (avoids py picking Python 2 if present)
    set "PYTHON=py -3"
  ) else (
    echo [ERROR] Python not found.
    echo Install Python 3.10+ from https://www.python.org/downloads/
    echo or Microsoft Store. Enable "Add python.exe to PATH" if offered.
    echo.
    pause
    exit /b 1
  )
)

echo [INFO] Using: %PYTHON%
%PYTHON% --version
echo.

if not exist ".venv" (
  echo [INFO] Creating virtual environment .venv ...
  %PYTHON% -m venv ".venv" || goto :fail
) else (
  echo [INFO] .venv already exists, reusing.
)

call ".venv\Scripts\activate.bat" || goto :fail

echo [INFO] Upgrading pip ...
python -m pip install -U pip wheel setuptools || goto :fail

if not exist "requirements.txt" (
  echo [ERROR] requirements.txt not found.
  goto :fail
)

echo [INFO] Installing requirements ...
python -m pip install -r requirements.txt || goto :fail

echo.
echo ========================================
echo   Setup finished
echo ========================================
echo   Next: double-click run.bat
echo   (menu: desktop / web / web+browser / shortcut)
echo ========================================
echo.
pause
exit /b 0

:fail
echo.
echo [ERROR] Setup failed. See messages above.
pause
exit /b 1
