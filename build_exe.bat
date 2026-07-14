@echo off
REM Build a single-file Windows exe for ping4.py
REM Usage: run this from an elevated Command Prompt or PowerShell
C:\Users\Administrator\anaconda3\python.exe -m pip install --upgrade pip setuptools wheel
C:\Users\Administrator\anaconda3\python.exe -m pip install -r "%~dp0requirements.txt"
C:\Users\Administrator\anaconda3\python.exe -m PyInstaller --noconfirm --onefile --windowed --name Ping4 "%~dp0ping4.py"
if %ERRORLEVEL% NEQ 0 (
  echo Build failed with error %ERRORLEVEL%
) else (
  echo Build succeeded. See dist\Ping4.exe
)
pause
