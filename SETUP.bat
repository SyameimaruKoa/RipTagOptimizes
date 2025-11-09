@echo off
chcp 65001 > nul
setlocal

rem --- ヘルプ表示 ---
if "%~1"=="-h" goto :HELP
if "%~1"=="--help" goto :HELP

echo ============================================================
echo  CD Workflow GUI Setup
echo ============================================================
echo.

rem --- Python Version Check ---
echo [1/4] Checking Python version...
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.12
    pause
    exit /b 1
)

python --version
echo.

rem --- Create Virtual Environment ---
echo [2/4] Creating virtual environment...
if exist ".venv\" (
    echo [INFO] Virtual environment already exists. Skipping...
) else (
    python -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [INFO] Virtual environment created successfully
)
echo.

rem --- Activate Virtual Environment ---
echo [3/4] Activating virtual environment...
call .venv\Scripts\activate.bat
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo [INFO] Virtual environment activated
echo.

rem --- Install Dependencies ---
echo [4/4] Installing dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo [INFO] Dependencies installed successfully
echo.

echo ============================================================
echo  Setup completed!
echo ============================================================
echo.
echo To start GUI, run:
echo   LAUNCH_GUI.bat
echo.
echo Or manually:
echo   .venv\Scripts\activate
echo   python main.py
echo.
pause
goto :EOF

:HELP
echo ============================================================
echo  CD Workflow GUI Setup
echo ============================================================
echo.
echo  Usage:
echo    SETUP.bat [options]
echo.
echo  Options:
echo    -h, --help    Show this help message
echo.
echo  Description:
echo    Creates Python virtual environment and installs required libraries.
echo    Run this once before first launch.
echo.
pause
goto :EOF
