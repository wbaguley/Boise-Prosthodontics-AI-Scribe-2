@echo off
echo 🌐 Quick ngrok setup for Boise Prosthodontics AI Scribe
echo.
echo 1. Make sure ngrok is installed (https://ngrok.com/download)
echo 2. Run this in a separate terminal: ngrok http 3051
echo 3. Copy the https URL and run: 
echo    powershell -ExecutionPolicy Bypass -File setup_ngrok.ps1 -NgrokUrl "YOUR_NGROK_URL"
echo.
echo For frontend access from phone, also run:
echo    ngrok http 3050
echo.
pause