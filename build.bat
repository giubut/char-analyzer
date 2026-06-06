@echo off
cd /d "%~dp0"
python --version >nul 2>&1 || (echo [ERROR] Python not found & pause & exit /b 1)
pip show pyinstaller >nul 2>&1 && echo [OK] PyInstaller || (pip install pyinstaller && echo [OK] PyInstaller installed)
echo [STEP] Building exe...
pyinstaller --clean char_analyzer.spec
if exist dist\char_analyzer.exe (echo [DONE] dist\char_analyzer.exe) else (echo [ERROR] Build failed)
pause
