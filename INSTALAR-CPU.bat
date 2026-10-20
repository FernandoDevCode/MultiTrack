@echo off
setlocal
cd /d "%~dp0"
echo MultiTrack - instalacao para Windows sem placa de video
echo Todos os componentes ficam nesta pasta. Nao precisa de administrador.
echo A primeira instalacao precisa de internet e pode demorar.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install-cpu.ps1"
if errorlevel 1 goto failed
if /I "%~1"=="--no-launch" exit /b 0
call "%~dp0START-MULTITRACK.bat"
exit /b %errorlevel%
:failed
echo.
echo A instalacao nao terminou. Confira .tmp\install-cpu.log e .tmp\install-cpu-bootstrap.log
echo Corrija o erro e execute este arquivo novamente para tentar continuar.
if /I not "%~1"=="--no-launch" pause
exit /b 1
