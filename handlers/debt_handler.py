import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from utils.parser import extract_debt_command, format_currency
from database.db_manager import save_transaction, update_user, find_user_id_by_username

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    sender = update.message.from_user
    update_user(sender.id, sender.username, sender.full_name)

    if update.message.chat.type not in ["group", "supergroup"]:
        return

    text = update.message.text
    parsed = extract_debt_command(text)
    
    if not parsed:
        if text.startswith(('/', '!', '@')):
            try:
                await update.message.set_reaction("❌")
                await asyncio.sleep(1)
                await update.message.delete()
            except Exception as e:
                logging.error(f"Error delete: {e}")
        return
        
    usernames, amount, reason, type_sign = parsed
    my_username = (sender.username or "").lower()
    others = [u for u in usernames if u.lower() != my_username]

    if not others:
         await update.message.reply_text("Ban khong the tu ghi no chinh minh!")
         return

    for tagged_username in others:
        real_id = find_user_id_by_username(tagged_username) or 0
        if real_id != 0 and real_id == sender.id:
            continue

        if type_sign == "-":
            creditor = {"id": sender.id, "name": sender.full_name or sender.username}
            debtor = {"id": real_id, "name": tagged_username}
        else:
            creditor = {"id": real_id, "name": tagged_username}
            debtor = {"id": sender.id, "name": sender.full_name or sender.username}

        save_transaction(
            group_id=update.message.chat.id,
            creditor=creditor,
            debtor=debtor,
            amount=amount,
            reason=reason,
            raw_message=text,
            created_by=sender.id,
            message_id=update.message.message_id
        )

    msg = f"✅ **Đã ghi nhận công nợ mới**\n"
    msg += f"📝 Lý do: {reason}\n"
    msg += f"💰 Số tiền: {format_currency(amount)}/người\n\n"
    
    if type_sign == "-":
        msg += f"👤 Người được trả: {sender.mention_html()}\n"
        msg += f"💸 Người nợ: {', '.join([f'@{u}' for u in others])}"
    else:
        msg += f"👤 Người được trả: {', '.join([f'@{u}' for u in others])}\n"
        msg += f"💸 Người nợ: {sender.mention_html()}"
    
    await update.message.reply_html(msg)
