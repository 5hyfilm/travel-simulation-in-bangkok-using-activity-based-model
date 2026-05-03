@echo off
chcp 65001 >nul
echo ==========================================
echo    Bangkok MATSim One-Click Runner (Win)
echo ==========================================

set "PROJECT_ROOT=%~dp0"

REM ─── Find Python ──────────────────────────────────────────────
set PYTHON_CMD=

REM 1. ลอง py launcher ก่อน
where py >nul 2>nul
if %ERRORLEVEL%==0 (
    set PYTHON_CMD=py
    goto :found_python
)

REM 2. ลอง python ใน PATH (conda activate แล้ว หรือ system Python)
where python >nul 2>nul
if %ERRORLEVEL%==0 (
    set PYTHON_CMD=python
    goto :found_python
)

REM 3. ค้นหา conda Python โดยตรงจาก common install paths (named envs first)
for %%P in (
    "%USERPROFILE%\miniconda3\envs\capstone\python.exe"
    "%USERPROFILE%\anaconda3\envs\capstone\python.exe"
    "%USERPROFILE%\AppData\Local\miniconda3\envs\capstone\python.exe"
    "%USERPROFILE%\AppData\Local\anaconda3\envs\capstone\python.exe"
    "%USERPROFILE%\anaconda3\python.exe"
    "%USERPROFILE%\miniconda3\python.exe"
    "%USERPROFILE%\AppData\Local\anaconda3\python.exe"
    "%USERPROFILE%\AppData\Local\miniconda3\python.exe"
    "C:\anaconda3\python.exe"
    "C:\miniconda3\python.exe"
    "C:\ProgramData\anaconda3\python.exe"
    "C:\ProgramData\miniconda3\python.exe"
) do (
    if exist %%P (
        set PYTHON_CMD=%%P
        goto :found_python
    )
)

REM 4. ค้นหา conda Python จาก conda info
for /f "delims=" %%i in ('conda info --base 2^>nul') do (
    if exist "%%i\python.exe" (
        set PYTHON_CMD=%%i\python.exe
        goto :found_python
    )
)

echo [ERROR] ไม่พบ Python กรุณาติดตั้ง Anaconda/Miniconda หรือ Python แล้วลองใหม่
pause
exit /b 1

:found_python
echo [INFO] ใช้ Python: %PYTHON_CMD%
%PYTHON_CMD% --version

REM ─── Check/Create venv ────────────────────────────────────────
echo.
echo ^>^>^> Checking virtual environment...
if not exist "%PROJECT_ROOT%venv\Scripts\python.exe" (
    echo [INFO] สร้าง virtual environment...
    %PYTHON_CMD% -m venv "%PROJECT_ROOT%venv"
    if errorlevel 1 (
        echo [ERROR] สร้าง venv ไม่สำเร็จ
        pause
        exit /b 1
    )
    echo [INFO] ติดตั้ง dependencies...
    "%PROJECT_ROOT%venv\Scripts\python.exe" -m pip install --upgrade pip >nul
    "%PROJECT_ROOT%venv\Scripts\python.exe" -m pip install -r "%PROJECT_ROOT%pipeline\requirements.txt"
    if errorlevel 1 (
        echo [ERROR] ติดตั้ง dependencies ไม่สำเร็จ
        pause
        exit /b 1
    )
) else (
    echo [INFO] พบ virtual environment แล้ว
)

set VENV_PYTHON="%PROJECT_ROOT%venv\Scripts\python.exe"

REM ─── Run pipeline ─────────────────────────────────────────────
echo.
echo ^>^>^> Starting simulation pipeline...
cd /d "%PROJECT_ROOT%pipeline"
%VENV_PYTHON% main.py
if errorlevel 1 (
    echo.
    echo [ERROR] Pipeline ล้มเหลว ดู error ด้านบน
    pause
    exit /b 1
)

echo.
echo ==========================================
echo    Run Completed
echo ==========================================
pause