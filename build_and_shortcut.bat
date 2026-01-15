@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem ==========================================
rem 設定（必要ならここだけ変更）
rem ==========================================
set APP_NAME=inventory-sales-tool
set ENTRY=app.py
set JSON_NAME=sales_inventory_tool.json

rem GUIアプリなら 1（Tkinter想定）、CLIなら 0
set IS_GUI=1

rem onefile: 1, onedir: 0
set ONEFILE=1

rem 配布先（リポジトリ直下に _dist\APP_NAME を作る）
set DIST_ROOT=%~dp0_dist
set INSTALL_DIR=%DIST_ROOT%\%APP_NAME%

rem 配布時の exe 名
set OUT_EXE_NAME=%APP_NAME%.exe

rem ショートカット名（デスクトップに作成）
set SHORTCUT_NAME=%APP_NAME%

rem ==========================================
rem 実行場所固定
rem ==========================================
cd /d "%~dp0"

rem ==========================================
rem 事前チェック
rem ==========================================
if not exist "%ENTRY%" (
  echo [ERROR] Entry file not found: "%ENTRY%"
  pause
  exit /b 1
)

if not exist "ui" (
  echo [ERROR] "ui" directory not found.
  pause
  exit /b 1
)

rem ==========================================
rem Python コマンド決定（py / python 両対応）
rem ==========================================
where python >nul 2>nul
if %errorlevel%==0 (
  set PYTHON=python
) else (
  where py >nul 2>nul
  if %errorlevel%==0 (
    set PYTHON=py
  ) else (
    echo [ERROR] Python not found. Install Python and add it to PATH.
    pause
    exit /b 1
  )
)

echo [INFO] Using Python: %PYTHON%

rem ==========================================
rem venv 構築と依存導入
rem ==========================================
if not exist ".venv" (
  %PYTHON% -m venv ".venv" || goto :fail
)

call ".venv\Scripts\activate.bat" || goto :fail

python -m pip install -U pip wheel setuptools || goto :fail

if exist "requirements.txt" (
  python -m pip install -r requirements.txt || goto :fail
)

python -m pip install -U pyinstaller || goto :fail

rem ==========================================
rem PyInstaller オプション構築
rem ==========================================
set PI_OPTS=--noconfirm --clean --name "%APP_NAME%"

if "%IS_GUI%"=="1" (
  set PI_OPTS=%PI_OPTS% --noconsole
)

if "%ONEFILE%"=="1" (
  set PI_OPTS=%PI_OPTS% --onefile
) else (
  set PI_OPTS=%PI_OPTS% --onedir
)

rem ==========================================
rem ビルド実行
rem ==========================================
echo [INFO] Building exe...
pyinstaller %PI_OPTS% "%ENTRY%" || goto :fail

rem ==========================================
rem 配布フォルダ準備
rem ==========================================
echo [INFO] Preparing install directory: "%INSTALL_DIR%"
if exist "%INSTALL_DIR%" rmdir /s /q "%INSTALL_DIR%"
mkdir "%INSTALL_DIR%" || goto :fail

rem ==========================================
rem ビルド成果物の配置
rem ==========================================
if "%ONEFILE%"=="1" (
  if not exist "dist\%APP_NAME%.exe" (
    echo [ERROR] Built exe not found: "dist\%APP_NAME%.exe"
    goto :fail
  )
  copy /y "dist\%APP_NAME%.exe" "%INSTALL_DIR%\%OUT_EXE_NAME%" >nul || goto :fail
  set TARGET_EXE=%INSTALL_DIR%\%OUT_EXE_NAME%
) else (
  if not exist "dist\%APP_NAME%\%APP_NAME%.exe" (
    echo [ERROR] Built onedir exe not found: "dist\%APP_NAME%\%APP_NAME%.exe"
    goto :fail
  )
  xcopy /e /i /y "dist\%APP_NAME%" "%INSTALL_DIR%" >nul || goto :fail
  set TARGET_EXE=%INSTALL_DIR%\%APP_NAME%.exe
)

rem ==========================================
rem JSON の配置（無ければ {} を生成）
rem ==========================================
if exist "%JSON_NAME%" (
  echo [INFO] Copy JSON: "%JSON_NAME%"
  copy /y "%JSON_NAME%" "%INSTALL_DIR%\%JSON_NAME%" >nul || goto :fail
) else (
  echo [WARN] "%JSON_NAME%" not found. Creating empty JSON in install dir.
  > "%INSTALL_DIR%\%JSON_NAME%" echo {}
)

rem ==========================================
rem デスクトップパス取得（PowerShell 不要）
rem ==========================================
set DESKTOP_DIR=%USERPROFILE%\Desktop
if not exist "%DESKTOP_DIR%" (
  echo [ERROR] Desktop folder not found: "%DESKTOP_DIR%"
  goto :fail
)

set SHORTCUT_PATH=%DESKTOP_DIR%\%SHORTCUT_NAME%.lnk

rem ==========================================
rem VBScript を生成してショートカット作成（PowerShell 不要）
rem ==========================================
set VBS=%TEMP%\_mkshortcut_%RANDOM%.vbs

> "%VBS%" echo Option Explicit
>>"%VBS%" echo Dim shell, sc
>>"%VBS%" echo Dim lnkPath, targetPath, workDir, iconPath
>>"%VBS%" echo lnkPath = "%SHORTCUT_PATH%"
>>"%VBS%" echo targetPath = "%TARGET_EXE%"
>>"%VBS%" echo workDir = "%INSTALL_DIR%"
>>"%VBS%" echo iconPath = "%TARGET_EXE%"
>>"%VBS%" echo Set shell = CreateObject("WScript.Shell")
>>"%VBS%" echo Set sc = shell.CreateShortcut(lnkPath)
>>"%VBS%" echo sc.TargetPath = targetPath
>>"%VBS%" echo sc.WorkingDirectory = workDir
>>"%VBS%" echo sc.IconLocation = iconPath
>>"%VBS%" echo sc.Save

cscript //nologo "%VBS%" || goto :fail
del "%VBS%" >nul 2>nul

echo.
echo [DONE] Build + install + shortcut completed.
echo        Install Dir: "%INSTALL_DIR%"
echo        Shortcut   : "%SHORTCUT_PATH%"
echo        Target EXE : "%TARGET_EXE%"
echo.
pause
exit /b 0

:fail
echo.
echo [ERROR] Failed. Check messages above.
pause
exit /b 1
