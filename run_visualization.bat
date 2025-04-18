@echo off
echo =========================================
echo      AirSIM CIS Real-Time Visualization
echo =========================================

:: Activate Anaconda environment
CALL C:\Users\jhand\anaconda3\Scripts\activate vertisim

:: Kill any process using port 8765 (WebSocket)
FOR /F "tokens=5" %%P IN ('netstat -ano ^| findstr :8765') DO (
    echo Killing existing process on port 8765: PID %%P
    taskkill /PID %%P /F > nul
)

:: Kill any process using port 8080 (HTTP server)
FOR /F "tokens=5" %%P IN ('netstat -ano ^| findstr :8080') DO (
    echo Killing existing process on port 8080: PID %%P
    taskkill /PID %%P /F > nul
)

:: Start HTTP server in web_client
echo Starting HTTP server on port 8080...
start cmd /k "cd visualization\web_client && python -m http.server 8080"

:: Small delay to ensure HTTP server starts
timeout /t 2 > nul

:: Start Python simulation
echo Starting UAM Simulation...
python main.py

echo =========================================
echo Simulation finished. Press any key to exit.
pause
