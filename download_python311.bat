@echo off
setlocal

rem === Cau hinh ===
set "PY_VERSION=3.11.9"
set "PY_URL=https://www.python.org/ftp/python/%PY_VERSION%/python-%PY_VERSION%-amd64.exe"
set "OUT_DIR=%USERPROFILE%\Downloads"
set "OUT_FILE=%OUT_DIR%\python-%PY_VERSION%-amd64.exe"

echo ==========================================
echo  Tai Python %PY_VERSION% (64-bit)
echo ==========================================
echo Nguon : %PY_URL%
echo Luu ve: %OUT_FILE%
echo.

rem === Tai file (dung PowerShell, co san tren Windows) ===
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%OUT_FILE%' -UseBasicParsing"

if errorlevel 1 (
    echo.
    echo [LOI] Tai that bai. Hay kiem tra ket noi mang.
    pause
    exit /b 1
)

if not exist "%OUT_FILE%" (
    echo [LOI] Khong tim thay file sau khi tai.
    pause
    exit /b 1
)

echo [OK] Tai xong: %OUT_FILE%
echo.

rem === Tu dong cai dat (khong hoi) ===
echo Dang cai dat (tu them vao PATH)...
"%OUT_FILE%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0
if errorlevel 1 (
    echo [LOI] Cai dat khong thanh cong.
) else (
    echo [OK] Cai dat hoan tat. Mo lai CMD roi go: python --version
)

echo.
pause
endlocal
