@echo off
cd /d "%~dp0"
echo გაშვება: %cd%
echo Python: 
python --version
echo.
python -m src.main
echo.
echo Exit code: %errorlevel%
pause
