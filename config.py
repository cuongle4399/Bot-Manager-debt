import os
import json
from dotenv import load_dotenv

# Mặc định load .env nếu có
load_dotenv()

CONFIG_FILE = "config.json"

# Hàm lấy cấu hình từ JSON hoặc Environment
def get_config(key, default=None):
    # Thử đọc từ config.json trước
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if key in data:
                    return data[key]
        except Exception:
            pass
    
    # Nếu không có trong JSON thì lấy từ .env/Hệ thống
    return os.getenv(key, default)

BOT_TOKEN = get_config("BOT_TOKEN")
DATABASE_PATH = os.path.join(os.getcwd(), "database", "bot_debt.db")
OWNER_ID = int(get_config("OWNER_ID", 0))
LOG_LEVEL = get_config("LOG_LEVEL", "INFO")

if not BOT_TOKEN:
    raise ValueError(f"BOT_TOKEN is missing! Please check {CONFIG_FILE} or .env file.")
