@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if /i "%~1"=="desktop" goto :desktop
if /i "%~1"=="web" goto :web
if /i "%~1"=="webopen" goto :webopen
if /i "%~1"=="shortcut" goto :shortcut

:menu
echo ========================================
echo   Inventory / Sales Tool - Run
echo ========================================
echo   1  Desktop app (Tkinter)
echo   2  Web server only (open http://127.0.0.1:8765 in browser)
echo   3  Web server + open browser (new window for server)
echo   4  Create desktop shortcut for option 3
echo   0  Exit
echo ========================================
set /p CH=Choose [0-4]: 
if "%CH%"=="1" goto :desktop
if "%CH%"=="2" goto :web
if "%CH%"=="3" goto :webopen
if "%CH%"=="4" goto :shortcut
if "%CH%"=="0" exit /b 0
echo Invalid choice.
timeout /t 2 /nobreak >nul
goto :menu

:desktop
if not exist ".venv\Scripts\activate.bat" (
  echo [ERROR] Run setup.bat first.
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
echo Starting desktop app ...
echo Keep this window open until you close the app.
echo.
python app.py
set "EC=%errorlevel%"
if not "%EC%"=="0" (
  echo.
  echo Exited with error code %EC%.
  pause
)
exit /b %EC%

:web
if not exist ".venv\Scripts\activate.bat" (
  echo [ERROR] Run setup.bat first.
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
echo.
echo ========================================
echo   Web UI server
echo ========================================
echo   1. Wait until the server starts below.
echo   2. Open a browser to:
echo        http://127.0.0.1:8765
echo   3. To stop: close this window or press Ctrl+C
echo.
echo   If "address already in use": set PORT=8766 before run.bat
echo ========================================
echo.
if defined PORT (
  echo [INFO] PORT=%PORT%
) else (
  echo [INFO] PORT=8765 (default)
)
echo.
python -m web
set "EC=%errorlevel%"
echo.
if not "%EC%"=="0" (
  echo Server stopped with error code %EC%.
  echo Another program may be using the port.
)
pause
exit /b %EC%

:webopen
if not exist ".venv\Scripts\activate.bat" (
  echo [ERROR] Run setup.bat first.
  pause
  exit /b 1
)
if "%PORT%"=="" (
  set "URLPORT=8765"
) else (
  set "URLPORT=%PORT%"
)
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
rem Trailing "\" before a closing quote breaks "cd /d" and can confuse start /D
start "Inventory Web Server" /D "%ROOT%" cmd /k "call .venv\Scripts\activate.bat & python -m web"
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:%URLPORT%/"
exit /b 0

:shortcut
set INSTALL_DIR=%~dp0
if "%INSTALL_DIR:~-1%"=="\" set "INSTALL_DIR=%INSTALL_DIR:~0,-1%"
set RUN_BAT=%INSTALL_DIR%\run.bat
if not exist "%RUN_BAT%" (
  echo [ERROR] Missing: "%RUN_BAT%"
  pause
  exit /b 1
)
set SHORTCUT_NAME=Inventory Sales Tool Web
set "DESKTOP_DIR=%USERPROFILE%\Desktop"
if not exist "%DESKTOP_DIR%" set "DESKTOP_DIR=%USERPROFILE%\OneDrive\Desktop"
if not exist "%DESKTOP_DIR%" (
  for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "Write-Output ([Environment]::GetFolderPath('Desktop'))"`) do set "DESKTOP_DIR=%%i"
)
if not exist "%DESKTOP_DIR%" (
  echo [ERROR] Desktop folder not found. Checked USERPROFILE\Desktop, OneDrive\Desktop, and PowerShell Desktop.
  pause
  exit /b 1
)
set SHORTCUT_PATH=%DESKTOP_DIR%\%SHORTCUT_NAME%.lnk
set ICON_PATH=%INSTALL_DIR%\icon.ico
rem Remove any existing shortcut first so Windows reads the new icon
if exist "%SHORTCUT_PATH%" del /q "%SHORTCUT_PATH%" >nul 2>nul
set VBS=%TEMP%\_mkrunshortcut_%RANDOM%.vbs
> "%VBS%" echo Option Explicit
>>"%VBS%" echo Dim shell, sc
>>"%VBS%" echo Dim lnkPath, targetPath, workDir
>>"%VBS%" echo lnkPath = "%SHORTCUT_PATH%"
>>"%VBS%" echo targetPath = "%RUN_BAT%"
>>"%VBS%" echo workDir = "%INSTALL_DIR%"
>>"%VBS%" echo Set shell = CreateObject("WScript.Shell")
>>"%VBS%" echo Set sc = shell.CreateShortcut(lnkPath)
>>"%VBS%" echo sc.TargetPath = targetPath
>>"%VBS%" echo sc.Arguments = "webopen"
>>"%VBS%" echo sc.WorkingDirectory = workDir
>>"%VBS%" echo sc.Description = "Start web UI and open browser"
if exist "%ICON_PATH%" (
  >>"%VBS%" echo sc.IconLocation = "%ICON_PATH%"
)
>>"%VBS%" echo sc.Save
cscript //nologo "%VBS%" || goto :shortcut_fail
del "%VBS%" >nul 2>nul
rem Refresh the shell icon cache so the new icon shows immediately
ie4uinit.exe -show >nul 2>nul
echo.
echo [DONE] Desktop shortcut created:
echo        "%SHORTCUT_PATH%"
echo.
echo If the icon still looks old, restart Explorer:
echo   taskkill /f /im explorer.exe ^&^& start explorer.exe
echo.
pause
exit /b 0

:shortcut_fail
echo.
echo [ERROR] Failed to create shortcut.
del "%VBS%" >nul 2>nul
pause
exit /b 1
