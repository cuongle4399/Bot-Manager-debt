import logging
import os
import asyncio
from telegram import Update, BotCommand, BotCommandScopeDefault, BotCommandScopeAllGroupChats
from telegram.ext import ApplicationBuilder, MessageHandler, filters, PrefixHandler
from apscheduler.schedulers.background import BackgroundScheduler
from config import BOT_TOKEN
from database.db_manager import init_db, get_all_groups
from handlers import command_handler, debt_handler
from services.debt_service import calculate_group_debts
from utils.parser import format_currency

async def post_init(application):
    commands = [
        BotCommand("no", "Xem nợ cá nhân"),
        BotCommand("ls", "Lịch sử nợ chưa tất toán"),
        BotCommand("help", "Xem hướng dẫn member"),
        BotCommand("admin", "Dành cho Admin/Owner"),
        BotCommand("allpaid", "Tất toán nợ cho ai đó"),
        BotCommand("undo", "Hoàn tác/Reply để xóa"),
        BotCommand("export", "Xuất file Excel cá nhân")
    ]
    await application.bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    await application.bot.set_my_commands(commands, scope=BotCommandScopeAllGroupChats())
    
    def run_weekly_job():
        asyncio.run_coroutine_threadsafe(send_weekly_reminders(application), application.loop)

    scheduler = BackgroundScheduler(timezone="Asia/Ho_Chi_Minh")
    scheduler.add_job(run_weekly_job, 'cron', day_of_week='sun', hour=9, minute=0)
    scheduler.start()

async def send_weekly_reminders(application):
    group_ids = get_all_groups()
    for group_id in group_ids:
        try:
            pair_debts, user_names = calculate_group_debts(group_id)
            if not pair_debts:
                continue
                
            res = "THÔNG BÁO CHỐT NỢ CUỐI TUẦN - CHỦ NHẬT\n\n"
            has_debt = False
            for (u1, u2), amount in pair_debts.items():
                if amount == 0: continue
                has_debt = True
                n1 = user_names.get(u1, f"User {u1}")
                n2 = user_names.get(u2, f"User {u2}")
                
                if amount > 0:
                    debtor_tag = f"@{n2}" if not n2.startswith("@") else n2
                    res += f"{debtor_tag} no {n1}: {format_currency(amount)}\n"
                else:
                    debtor_tag = f"@{n1}" if not n1.startswith("@") else n1
                    res += f"{debtor_tag} no {n2}: {format_currency(abs(amount))}\n"
            
            if has_debt:
                res += "\nHay thu xep thanh toan cho nhau nhe!"
                await application.bot.send_message(chat_id=group_id, text=res)
        except Exception as e:
            logging.error(f"Error reminder: {e}")

def main():
    if not os.path.exists("logs"):
        os.makedirs("logs")

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        handlers=[
            logging.FileHandler("logs/bot.log", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    
    init_db()
    
    application = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    
    prefixes = ['/', '!', '!!']
    application.add_handler(PrefixHandler(prefixes, "start", command_handler.start))
    application.add_handler(PrefixHandler(prefixes, "myid", command_handler.myid_command))
    application.add_handler(PrefixHandler(prefixes, "idgroups", command_handler.idgroups_command))
    application.add_handler(PrefixHandler(prefixes, "help", command_handler.help_command))
    application.add_handler(PrefixHandler(prefixes, "admin", command_handler.admin_command))
    application.add_handler(PrefixHandler(prefixes, "no", command_handler.no_command))
    application.add_handler(PrefixHandler(prefixes, "ls", command_handler.lichsu_command))
    application.add_handler(PrefixHandler(prefixes, "undo", command_handler.undo_command))
    application.add_handler(PrefixHandler(prefixes, "nhacno", command_handler.nhacno_command))
    application.add_handler(PrefixHandler(prefixes, "allpaid", command_handler.allpaid_command))
    application.add_handler(PrefixHandler(prefixes, "clear", command_handler.clear_command))
    application.add_handler(PrefixHandler(prefixes, "export", command_handler.export_command))
    application.add_handler(PrefixHandler(prefixes, "exportno", command_handler.exportno_command))
    
    text_filter = filters.TEXT & (~filters.COMMAND)
    application.add_handler(MessageHandler(text_filter, debt_handler.handle_message))
    
    unknown_cmd_filter = filters.Regex(r'^[!/]')
    application.add_handler(MessageHandler(unknown_cmd_filter, debt_handler.handle_message))
    
    application.run_polling()

if __name__ == '__main__':
    main()
