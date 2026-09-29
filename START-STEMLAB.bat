@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
  echo StemLab local runtime not found in .venv.
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
set "PATH=%CD%\tools\ffmpeg\bin;%CD%\.venv\Scripts;%PATH%"

start "StemLab" ".venv\Scripts\pythonw.exe" -m stemlab.ui
exit /b 0
