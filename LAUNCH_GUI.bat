@echo off
chcp 65001 > nul
setlocal

rem --- ヘルプ表示 ---
if "%~1"=="-h" goto :HELP
if "%~1"=="--help" goto :HELP
if "%~1"=="" if not exist ".venv\Scripts\activate.bat" if not exist "main.py" goto :HELP

rem --- 仮想環境の探索とアクティベート ---
if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo [WARNING] Virtual environment not found.
    echo Trying to run with system Python...
)

rem --- GUI起動 ---
echo [INFO] Starting CD Workflow GUI...
python main.py %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] GUI exited with error code: %ERRORLEVEL%
    pause
)
goto :EOF

:HELP
echo ============================================================
echo  CD Workflow GUI Launcher
echo ============================================================
echo.
echo  Usage:
echo    LAUNCH_GUI.bat [options]
echo.
echo  Options:
echo    -h, --help    Show this help message
echo.
echo  Description:
echo    Automatically detects and activates Python virtual environment (.venv),
echo    then launches the CD Workflow GUI (main.py).
echo.
pause
goto :EOF
