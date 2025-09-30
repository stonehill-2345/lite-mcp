@echo off
REM LiteMCP Web Frontend Startup Script (Windows)

setlocal enabledelayedexpansion

echo 🚀 LiteMCP Web Frontend Startup Script
echo ================================

REM Check Node.js environment
echo [INFO] Checking Node.js environment...
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed! Please install Node.js version 16+
    echo Installation method: Visit https://nodejs.org/
    pause
    exit /b 1
)

REM Get Node.js version
for /f "tokens=1 delims=v" %%a in ('node --version') do set NODE_VERSION=%%a
for /f "tokens=1 delims=." %%a in ("!NODE_VERSION!") do set MAJOR_VERSION=%%a

if !MAJOR_VERSION! LSS 16 (
    echo [ERROR] Node.js version is too low! Requires version 16+
    node --version
    pause
    exit /b 1
)

echo [SUCCESS] Node.js environment check passed
node --version

REM Check npm
echo [INFO] Checking npm...
npm --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm is not installed! Please install npm
    pause
    exit /b 1
)
echo [SUCCESS] npm version:
npm --version

REM Install dependencies
echo [INFO] Checking and installing frontend dependencies...
if not exist "node_modules" (
    echo [INFO] Installing dependencies...
    npm install
    if errorlevel 1 (
        echo [ERROR] Dependency installation failed
        pause
        exit /b 1
    )
    echo [SUCCESS] Dependencies installed successfully
) else (
    echo [INFO] Dependencies already exist, skipping installation
)

REM Check backend service
echo [INFO] Checking backend service status...
REM Get API URL from environment or use default
if not defined VITE_API_BASE_URL set VITE_API_BASE_URL=http://localhost:9000
curl -s "%VITE_API_BASE_URL%/api/v1/health" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Backend service is not started, please start the backend service first:
    echo   cd ..
    echo   scripts\manage.bat up
    echo.
    echo [INFO] Continuing to start frontend service...
) else (
    echo [SUCCESS] Backend service is running normally (%VITE_API_BASE_URL%)
)

REM Start development server
echo [INFO] Starting frontend development server...
echo [INFO] Service address: http://localhost:2345
echo [INFO] Press Ctrl+C to stop the service
echo.

npm run dev

pause