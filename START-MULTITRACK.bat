@echo off
setlocal
cd /d "%~dp0"

if not exist "tools\python312\python.exe" (
  echo MultiTrack bundled Python not found in tools\python312.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\pythonw.exe" (
  echo MultiTrack local runtime not found in .venv.
  pause
  exit /b 1
)

set "TEMP=%CD%\.tmp"
set "TMP=%CD%\.tmp"
set "PIP_CACHE_DIR=%CD%\.cache\pip"
set "TORCH_HOME=%CD%\.cache\torch"
set "HF_HOME=%CD%\.cache\huggingface"
set "XDG_CACHE_HOME=%CD%\.cache"
set "MPLCONFIGDIR=%CD%\.cache\matplotlib"
set "AUDIO_SEPARATOR_MODEL_DIR=%CD%\models"
set "PYTHONUTF8=1"
set "PATH=%CD%\tools\ffmpeg\bin;%CD%\.venv\Scripts;%PATH%"

if not exist ".tmp" mkdir ".tmp"
"tools\python312\python.exe" -X utf8 "scripts\repair-local-runtime.py" > ".tmp\startup-check.log" 2>&1
if errorlevel 1 goto startup_failed
".venv\Scripts\python.exe" -X utf8 -c "import stemlab.ui" >> ".tmp\startup-check.log" 2>&1
if errorlevel 1 goto startup_failed

start "MultiTrack" ".venv\Scripts\pythonw.exe" -m stemlab.ui
exit /b 0

:startup_failed
echo MultiTrack could not start. Diagnostic log: %CD%\.tmp\startup-check.log
type ".tmp\startup-check.log"
pause
exit /b 1
