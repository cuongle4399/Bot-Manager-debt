@echo off
TITLE Telegram Debt Bot - Auto Setup
chcp 65001 > nul

:: Kiểm tra Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python chưa được cài đặt hoặc chưa được thêm vào PATH.
    echo Vui lòng cài đặt Python tại https://www.python.org/
    pause
    exit /b
)

:: Kiểm tra và tạo môi trường ảo
if not exist "venv" (
    echo [INFO] Đang tạo môi trường ảo (venv)...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Không thể tạo môi trường ảo.
        pause
        exit /b
    )
    echo [INFO] Đã tạo venv thành công.
)

:: Kích hoạt venv và cài đặt dependencies
echo [INFO] Đang kích hoạt môi trường ảo...
call venv\Scripts\activate

echo [INFO] Kiểm tra và cập nhật thư viện (requirements.txt)...
python -m pip install --upgrade pip
pip install -r requirements.txt

:: Kiểm tra file config.json
if not exist "config.json" (
    if exist "config.json.example" (
        echo [WARNING] Không tìm thấy config.json. Đang tạo từ bản mẫu...
        copy config.json.example config.json
        echo [IMPORTANT] Hãy mở file config.json và điền BOT_TOKEN của bạn!
        notepad config.json
    ) else (
        echo [ERROR] Thiếu file config.json và config.json.example!
    )
)

:: Chạy bot
echo [INFO] Đang khởi động Bot...
python bot.py

echo.
echo Bot đã dừng.
pause
