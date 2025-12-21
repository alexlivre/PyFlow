@echo off
echo Stopping any existing PyFlow containers...
docker-compose down

echo.
echo Starting PyFlow via Docker Compose (Dev Mode)...
echo.
echo Note: First time startup might take a few minutes to install dependencies and compile.
echo.
echo =========================================================
echo   IMPORTANT: The logs may refer to http://0.0.0.0:3000
echo   PLEASE IGNORE THAT.
echo.
echo   Access the UI at: http://localhost:3000
echo =========================================================
echo.
echo Building and starting containers...
docker-compose up --build

echo.
pause
