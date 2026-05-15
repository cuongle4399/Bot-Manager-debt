@echo off
echo ======================================================
echo   BUILDING BOT MANAGER DEBT TO EXE (ONEFILE)
echo ======================================================

:: Kiem tra va cai dat PyInstaller neu chua co
pip install pyinstaller

:: Tien hanh build
:: --onefile: Dong goi thanh 1 file duy nhat
:: --name: Ten file exe dau ra
:: --clean: Don dep cache truoc khi build

pyinstaller --onefile --name "BotManager" --clean ^
 --add-data "database;database" ^
 --add-data "handlers;handlers" ^
 --add-data "services;services" ^
 --add-data "utils;utils" ^
 bot.py

:: Copy file config vao thu muc dist de dung kem voi exe
if exist config.json (
    copy config.json dist\config.json
    echo.
    echo [+] Da copy config.json vao thu muc dist.
)

echo.
echo ======================================================
echo   BUILD HOAN TAT! File exe nam trong thu muc 'dist'
echo ======================================================
pause