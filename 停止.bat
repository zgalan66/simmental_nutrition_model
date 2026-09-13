@echo off
chcp 65001 >nul
title Stop Server

echo Finding process on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo Killing PID: %%a
    taskkill /PID %%a /F >nul 2>&1
)

echo.
echo [OK] Server stopped
timeout /t 2 >nul