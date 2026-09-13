@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 西门塔尔公牛营养模型系统

echo ================================================
echo   Simmental Bull Nutrition Model System
echo ================================================
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo [!] venv not found, creating...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
) else (
    call .venv\Scripts\activate.bat
)

if not exist "simmental_nutrition.db" (
    echo [!] DB not found, initializing...
    python init_project.py
    if exist "import_feeds.py" (
        if exist "data\原料含量.xlsx" (
            python import_feeds.py
        )
    )
)

echo.
echo [*] Starting server...
echo.
echo   Web UI:    http://localhost:8000/ui
echo   API Docs:  http://localhost:8000/docs
echo   Health:    http://localhost:8000/health
echo.
echo   Press Ctrl+C to stop
echo.
echo ================================================
echo.

uvicorn main:app --host 0.0.0.0 --port 8000

echo.
echo [*] Server stopped
pause