@echo off
setlocal

set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

echo ==============================================
echo   OddMinutes Installer
echo ==============================================
echo.

echo [1/4] Checking Python environment...
python --version 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python not found!
    echo    Please install Python 3.10+ first.
    echo    Download: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
echo OK: Python environment check passed
echo.

echo [2/4] Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1
echo OK: pip upgraded
echo.

echo [3/4] Installing core dependencies...
echo       This may take a few minutes...
echo.

python -m pip install --prefer-binary Django==5.0.7 djangorestframework==3.15.2 django-cors-headers==4.4.0
python -m pip install --prefer-binary channels==4.1.0 channels-redis==4.2.0 daphne==4.1.2
python -m pip install --prefer-binary python-dotenv==1.0.1 requests==2.32.3 websockets>=13.0.0,<15.1.0 aiosqlite==0.21.0
python -m pip install --prefer-binary pydantic>=2.9.0,<3.0.0 pydantic-ai-slim[openai,anthropic,groq]==0.2.15 ollama==0.5.2
python -m pip install --prefer-binary pillow>=10.0.0 pystray>=0.19.0
python -m pip install --prefer-binary pywin32>=306 keyboard>=0.13.0 pynput>=1.7.0
python -m pip install --prefer-binary markdown>=3.6 bleach>=6.0.0 python-dateutil>=2.9.0
python -m pip install --prefer-binary numpy>=1.26.4,<3.0.0 scipy>=1.18.0,<2.0.0
python -m pip install --prefer-binary ffmpeg-python==0.2.0 pydub==0.25.1

echo.
echo [3b/4] Installing optional audio dependencies...
echo       (These may require additional system libraries)
echo.

python -m pip install --prefer-binary sounddevice>=0.4.0 2>nul || echo WARN: sounddevice skipped
python -m pip install --prefer-binary pyaudio>=0.2.10 2>nul || echo WARN: pyaudio skipped (requires portaudio)

echo.
echo OK: Dependencies installed
echo.

echo [4/4] Creating shortcuts...
python "%PROJECT_DIR%\create_shortcut.py"

if errorlevel 1 (
    echo.
    echo WARN: Shortcut creation failed, run manually:
    echo    python create_shortcut.py
) else (
    echo OK: Shortcuts created
)

echo.
echo ==============================================
echo   Installation Complete!
echo ==============================================
echo.
echo --- Usage:
echo    1. Double-click desktop shortcut "小奥会议纪要"
echo    2. First launch will install missing dependencies
echo    3. Browser will open http://127.0.0.1:9011
echo.
echo DIR: %PROJECT_DIR%
echo LOG: %PROJECT_DIR%\logs\launcher.log
echo.
pause