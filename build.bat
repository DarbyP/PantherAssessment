@echo off
echo Building Panther Assessment for Windows...
echo.

REM Check if pyinstaller is installed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
)

REM Build the application
pyinstaller build_windows.spec

if errorlevel 1 (
    echo.
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo Build complete!
echo Executable location: dist\PantherAssessment\PantherAssessment.exe
echo.
echo You can now distribute the entire dist\PantherAssessment folder
pause
