# Bot Quản Lý Nợ Telegram

### 1. Cấu hình
Tạo file `config.json` và điền:
```json
{
  "BOT_TOKEN": "your_bot_token_here",
  "OWNER_ID": 12345678,
  "LOG_LEVEL": "INFO"
}
```

### 2. Cài đặt
```bash
pip install -r requirements.txt
```

### 3. Chạy Bot
```bash
python bot.py
```

### 4. Lệnh cơ bản
* `@user -50k`: Ghi nợ (Họ nợ mình)
* `@user +50k`: Ghi nợ (Mình nợ họ)
* `!no`: Xem nợ bản thân
* `!allpaid @user`: Tất toán nợ
* `!admin`: Menu quản trị
