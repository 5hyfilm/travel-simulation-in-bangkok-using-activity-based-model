@echo off
echo ==========================================
echo    Bangkok MATSim One-Click Runner (Win)
echo ==========================================

REM Define the project root directory
set "PROJECT_ROOT=%~dp0"

REM 1. Activate Python Virtual Environment
echo ^>^^>^^> Activating virtual environment...
if exist "%PROJECT_ROOT%venv\Scripts\activate.bat" (
    call "%PROJECT_ROOT%venv\Scripts\activate.bat"
    echo Virtual environment activated successfully.
) else (
    echo Warning: Virtual environment not found at %PROJECT_ROOT%venv.
    echo Attempting to run with default system Python...
)

REM 2. Run the main pipeline (which now handles both preprocessing and MATSim)
echo ^>^^>^^> Starting the simulation pipeline...
cd /d "%PROJECT_ROOT%preprocess" || exit /b
python main.py

echo ==========================================
echo    Run Completed
echo ==========================================
pause
