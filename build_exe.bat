@echo off
setlocal

REM Build a single-file Windows EXE for ping.py
REM Usage: run this from Command Prompt or PowerShell

set "SCRIPT_DIR=%~dp0"
set "PYTHON_EXE="

if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
  set "PYTHON_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"
) else if exist "%USERPROFILE%\anaconda3\python.exe" (
  set "PYTHON_EXE=%USERPROFILE%\anaconda3\python.exe"
) else (
  where py >nul 2>nul
  if not errorlevel 1 (
    for /f "usebackq delims=" %%I in (`py -3 -c "import sys; print(sys.executable)" 2^>nul`) do set "PYTHON_EXE=%%I"
  )
)

if not defined PYTHON_EXE (
  where python >nul 2>nul
  if not errorlevel 1 (
    for /f "usebackq delims=" %%I in (`where python`) do set "PYTHON_EXE=%%I"
  )
)

if not defined PYTHON_EXE (
  echo Could not find Python. Install Python or activate your environment and try again.
  exit /b 1
)

echo Using Python: %PYTHON_EXE%

"%PYTHON_EXE%" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
  echo Failed to upgrade packaging tools.
  exit /b %ERRORLEVEL%
)

"%PYTHON_EXE%" -m pip install -r "%SCRIPT_DIR%requirements.txt"
if errorlevel 1 (
  echo Failed to install Python dependencies.
  exit /b %ERRORLEVEL%
)

"%PYTHON_EXE%" -m PyInstaller --noconfirm --clean --onefile --windowed --name Pinging --distpath "%SCRIPT_DIR%dist" --workpath "%SCRIPT_DIR%build" "%SCRIPT_DIR%ping.py"
if errorlevel 1 (
  echo Build failed with error %ERRORLEVEL%
  exit /b %ERRORLEVEL%
)

echo Build succeeded. See dist\Pinging.exe
endlocal
pause
