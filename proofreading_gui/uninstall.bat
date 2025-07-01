@echo off
echo Uninstalling Proofreading GUI...
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This uninstaller requires Administrator privileges.
    echo Please right-click on uninstall.bat and select "Run as administrator"
    echo.
    pause
    exit /b 1
)

REM Set installation directory
set INSTALL_DIR=%PROGRAMFILES%\ProofreadingGUI

REM Remove desktop shortcut
set DESKTOP=%USERPROFILE%\Desktop
set SHORTCUT=%DESKTOP%\Proofreading GUI.lnk

if exist "%SHORTCUT%" (
    echo Removing desktop shortcut...
    del "%SHORTCUT%"
    if errorlevel 1 (
        echo WARNING: Failed to remove desktop shortcut.
    )
)

REM Remove installation directory and files
if exist "%INSTALL_DIR%\" (
    echo Removing installed files...
    rmdir /s /q "%INSTALL_DIR%"
    if exist "%INSTALL_DIR%\" (
        echo WARNING: Failed to remove installation directory: %INSTALL_DIR%
    ) else (
        echo Installation directory removed: %INSTALL_DIR%
    )
) else (
    echo Installation directory not found: %INSTALL_DIR%
)

echo.
echo Uninstallation complete!
echo.
pause
