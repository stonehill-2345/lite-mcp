@echo off
REM LiteMCP Framework management script wrapper (Windows)
REM Simplifies calling the Python management tool, supporting all original features
REM
REM Usage examples:
REM   scripts\manage.bat up
REM   scripts\manage.bat down
REM   scripts\manage.bat ps
REM   scripts\manage.bat up example

setlocal

REM Get script directory and project root directory
set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."
set "PYTHON_MANAGER=%SCRIPT_DIR%manage.py"

REM Check if Python management script exists
if not exist "%PYTHON_MANAGER%" (
    echo ❌ Error: Python management script not found: %PYTHON_MANAGER%
    exit /b 1
)

REM Check Python environment
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
    goto :found_python
)

python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python3"
    goto :found_python
)

py --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=py"
    goto :found_python
)

echo ❌ Error: Python environment not found (requires python, python3, or py command)
    echo    Please install Python 3.12+ and ensure it's available in PATH
exit /b 1

:found_python
REM Switch to project root directory
cd /d "%PROJECT_DIR%"

REM Check if using Poetry environment
poetry --version >nul 2>&1
if %errorlevel% equ 0 (
    if exist "%PROJECT_DIR%\pyproject.toml" (
        REM Execute using Poetry environment
        poetry run %PYTHON_CMD% "%PYTHON_MANAGER%" %*
        goto :end
    )
)

REM Execute directly with Python
%PYTHON_CMD% "%PYTHON_MANAGER%" %*

:end