@echo off
setlocal enabledelayedexpansion
title Building ReadAloud Desktop AI Installer

echo ========================================================
echo       ReadAloud Desktop AI - Windows 11 Build Tool
echo ========================================================
echo.

cd /d "%~dp0"

echo [1/3] Checking dependencies...
python -m pip install -r requirements.txt >nul 2>&1

echo [2/3] Compiling standalone executable with PyInstaller...
python -m PyInstaller --clean -y installer\ReadAloud.spec
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed!
    pause
    exit /b 1
)

echo [3/3] Compiling Windows Setup Installer with Inno Setup...
set "ISCC_PATH=C:\Users\%USERNAME%\AppData\Local\Programs\Inno Setup 6\ISCC.exe"
if not exist "!ISCC_PATH!" (
    set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)
if not exist "!ISCC_PATH!" (
    set "ISCC_PATH=C:\Program Files\Inno Setup 6\ISCC.exe"
)

if exist "!ISCC_PATH!" (
    echo Found Inno Setup at: "!ISCC_PATH!"
    if not exist "output" mkdir "output"
    "!ISCC_PATH!" "installer\setup.iss"
    if errorlevel 1 (
        echo [ERROR] Inno Setup compilation failed!
        pause
        exit /b 1
    )
    echo.
    echo ========================================================
    echo SUCCESS: Windows Installer created at:
    echo %~dp0output\ReadAloud-Setup-v1.0.exe
    echo ========================================================
) else (
    echo [WARNING] Inno Setup compiler (ISCC.exe) not found.
    echo Standalone single-file executable built at: %~dp0dist\ReadAloudAI.exe
)

echo.
pause
