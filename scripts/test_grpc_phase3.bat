@echo off
REM Test Phase3 gRPC Service

echo ========================================
echo Phase3 gRPC Service Test
echo ========================================

cd /d %~dp0..

echo.
echo Before testing, please ensure:
echo   1. gRPC server is running
echo   2. GOOGLE_API_KEY is set
echo.
echo If server is not running, execute first:
echo   scripts\start_grpc_server.bat
echo.
pause

echo.
echo Starting tests...
echo.
python tests\test_grpc_phase3.py

echo.
echo ========================================
echo Test completed
echo ========================================
pause

