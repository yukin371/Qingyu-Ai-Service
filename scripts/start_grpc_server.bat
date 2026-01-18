@echo off
REM Start Phase3 gRPC Server

echo ========================================
echo Phase3 gRPC Server Startup
echo ========================================

cd /d %~dp0..

REM Check API Key
if "%GOOGLE_API_KEY%"=="" (
    echo.
    echo ERROR: GOOGLE_API_KEY environment variable is not set
    echo.
    echo Please set API key first:
    echo   set GOOGLE_API_KEY=your_api_key_here
    echo.
    pause
    exit /b 1
)

echo.
echo API Key is set
echo.
echo [1/2] Checking dependencies...
python -c "import grpc; import google.generativeai" 2>NUL
if errorlevel 1 (
    echo Missing dependencies, installing...
    pip install -r requirements.txt
)

echo.
echo [2/2] Starting gRPC server...
echo.
echo ========================================
python src\grpc_service\server.py --host 0.0.0.0 --port 50051

pause

