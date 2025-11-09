@echo off
chcp 65001 > nul
setlocal

rem --- スクリプトのディレクトリに移動 ---
cd /d "%~dp0"

rem --- ヘルプ表示 ---
if "%~1"=="-h" goto :HELP
if "%~1"=="--help" goto :HELP

rem --- 初回セットアップチェック ---
if not exist ".venv\Scripts\activate.bat" (
    echo ============================================================
    echo  初回セットアップが必要です
    echo ============================================================
    echo.
    echo 仮想環境が見つかりません。自動セットアップを開始します。
    echo.
    goto :SETUP
)

rem --- 依存関係チェック（requirements.txtの更新検出） ---
if exist ".venv\.setup_complete" (
    rem requirements.txtが.setup_completeより新しい場合は再インストール
    for %%A in (requirements.txt) do set req_time=%%~tA
    for %%B in (.venv\.setup_complete) do set setup_time=%%~tB
    
    rem 簡易比較：.setup_completeが存在しない、またはrequirements.txtが更新された場合
    if not exist ".venv\.setup_complete" goto :UPDATE_DEPS
) else (
    goto :UPDATE_DEPS
)

goto :LAUNCH

:UPDATE_DEPS
echo [INFO] 依存関係を更新中...
call .venv\Scripts\activate.bat
pip install -r requirements.txt --quiet
if %ERRORLEVEL% neq 0 (
    echo [WARNING] 依存関係の更新に失敗しました
) else (
    echo. > .venv\.setup_complete
    echo [INFO] 依存関係の更新完了
)
echo.

:LAUNCH
rem --- 仮想環境のアクティベート ---
echo [INFO] Activating virtual environment...
call .venv\Scripts\activate.bat

rem --- GUI起動 ---
echo [INFO] Starting CD Workflow GUI...
python main.py %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] GUI exited with error code: %ERRORLEVEL%
    pause
)
goto :EOF

:SETUP
echo [1/3] Checking Python version...
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python が見つかりません。Python 3.12以降をインストールしてください。
    echo.
    echo ダウンロード: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
python --version
echo.

echo [2/3] Creating virtual environment...
python -m venv .venv
if %ERRORLEVEL% neq 0 (
    echo [ERROR] 仮想環境の作成に失敗しました
    pause
    exit /b 1
)
echo [INFO] 仮想環境を作成しました
echo.

echo [3/3] Installing dependencies...
call .venv\Scripts\activate.bat
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [ERROR] 依存関係のインストールに失敗しました
    pause
    exit /b 1
)
echo. > .venv\.setup_complete
echo [INFO] 依存関係をインストールしました
echo.

echo ============================================================
echo  セットアップ完了！
echo ============================================================
echo.
echo GUIを起動します...
echo.
timeout /t 2 /nobreak >nul
goto :LAUNCH

:HELP
echo ============================================================
echo  CD取り込み自動化ワークフロー GUI
echo ============================================================
echo.
echo  使い方:
echo    LAUNCH_GUI.bat [オプション]
echo.
echo  オプション:
echo    -h, --help    このヘルプを表示
echo.
echo  機能:
echo    - 初回実行時: 自動で仮想環境を作成し、必要なライブラリをインストール
echo    - 2回目以降: 仮想環境をアクティベートしてGUIを起動
echo    - requirements.txt更新時: 自動で依存関係を再インストール
echo.
echo  初回セットアップが必要な場合、自動的に実行されます。
echo  Python 3.12以降が必要です。
echo.
pause
goto :EOF
