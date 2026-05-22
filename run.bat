@echo off
cd /d "%~dp0"
python -m src.main
if errorlevel 1 (
    echo.
    echo ERROR: პროგრამა ვერ გაეშვა. Error ზემოთ ნახე.
    pause
)
