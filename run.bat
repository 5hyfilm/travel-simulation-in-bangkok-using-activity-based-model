@echo off
echo ==========================================
echo    Bangkok MATSim One-Click Runner (Win)
echo ==========================================

REM Define the project root directory
set "PROJECT_ROOT=%~dp0"

REM Find the correct Python command (py or python)
set PYTHON_CMD=
where py >nul 2>nul
if %ERRORLEVEL%==0 (
    set PYTHON_CMD=py
) else (
    where python >nul 2>nul
    if %ERRORLEVEL%==0 (
        set PYTHON_CMD=python
    ) else (
        echo [ERROR] Python is not installed or not added to PATH!
        echo Please install Python from python.org and try again.
        pause
        exit /b 1
    )
)

REM 1. Activate or Create Python Virtual Environment
echo ^>^^>^^> Checking virtual environment...
if not exist "%PROJECT_ROOT%venv\Scripts\activate.bat" (
    echo [INFO] Virtual environment not found. Creating one automatically...
    %PYTHON_CMD% -m venv "%PROJECT_ROOT%venv"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [INFO] Installing dependencies...
    call "%PROJECT_ROOT%venv\Scripts\activate.bat"
    pip install -r "%PROJECT_ROOT%preprocess\requirements.txt"
) else (
    call "%PROJECT_ROOT%venv\Scripts\activate.bat"
)

echo Virtual environment activated successfully.

REM 2. Run the main pipeline (which now handles both preprocessing and MATSim)
echo ^>^^>^^> Starting the simulation pipeline...
cd /d "%PROJECT_ROOT%preprocess" || exit /b
python main.py

echo ==========================================
echo    Run Completed
echo ==========================================
pause
