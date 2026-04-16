import os
import re
import sqlite3
import asyncio
import io
from telegram import Update
from telegram.ext import ContextTypes
from services.debt_service import calculate_group_debts, get_my_debts
from utils.parser import format_currency
from config import OWNER_ID
from database.db_manager import (
    get_all_groups, 
    find_user_id_by_username, 
    get_debts_in_group, 
    delete_transaction, 
    save_transaction
)
from openpyxl import Workbook
from openpyxl.styles import Font

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id == OWNER_ID:
        try:
            conn = sqlite3.connect("database/bot_debt.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transactions")
            conn.commit()
            conn.close()
            
            current_msg_id = update.message.id
            count = 0
            streak_fail = 0
            for i in range(1, 501):
                try:
                    await context.bot.delete_message(chat_id=update.message.chat.id, message_id=current_msg_id - i)
                    count += 1
                    streak_fail = 0
                    if count % 10 == 0:
                        await asyncio.sleep(0.05)
                except:
                    streak_fail += 1
                    if streak_fail >= 15:
                        break
                    continue
            await update.message.reply_text(f"HE THONG DA RESET. Da xoa toan bo no va {count} tin nhan.")
        except Exception as e:
            await update.message.reply_text(f"Loi khi reset: {e}")
    else:
        await update.message.reply_text("Bot Quan Ly Cong No da san sang. Go !help de xem huong dan.")

async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"ID Telegram của bạn: `{update.message.from_user.id}`", parse_mode="Markdown")

async def idgroups_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return
        
    group_ids = get_all_groups()
    if not group_ids:
        await update.message.reply_text("Chưa có danh sách nhóm nào trong bộ nhớ.")
        return
        
    res = "📊 **DANH SÁCH GROUP ID ĐANG HOẠT ĐỘNG**\n\n"
    for gid in group_ids:
        res += f"• `{gid}`\n"
    await update.message.reply_text(res, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📜 **HƯỚNG DẪN BIẾT DÙNG BOT QUẢN LÝ NỢ**

📝 **CÁCH GHI NỢ:**
• `@user -50k [lý do]` : Bạn cho @user vay (Ghi nợ cho họ)
• `@user +50k [lý do]` : Bạn vay từ @user (Ghi nợ cho chính mình)
• `@u1 @u2 -50k [lý do]` : Ghi nợ cho nhiều người cùng lúc

📊 **TRA CỨU THÔNG TIN:**
• `!no` : Xem danh sách các khoản nợ của chính bạn
• `!no all` : Xem tổng hợp công nợ của tất cả thành viên
• `!ls` : Xem lịch sử giao dịch gần đây của bạn
• `!ls @user` : Xem lịch sử nợ chi tiết giữa bạn và @user
• `!myid` : Lấy ID Telegram của bạn

📢 **NHẮC NỢ & THANH TOÁN:**
• `!nhacno` : Gửi tin nhắn nhắc nhở tất cả những ai đang nợ bạn
• `!allpaid @user` : Xác nhận @user đã trả hết sạch nợ cho bạn
• `!undo` : Hoàn tác (xóa) đơn nợ vừa ghi 
   _(Hoặc Reply tin nhắn nợ bất kỳ và gõ !undo để xóa đơn đó)_

📥 **TIỆN ÍCH:**
• `!export` : Xuất file Excel lịch sử nợ cá nhân để đối soát

💡 *Lưu ý: Bạn chỉ có thể hoàn tác hoặc tất toán các khoản nợ liên quan đến chính mình.*
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    is_admin = False
    if user_id == OWNER_ID:
        is_admin = True
    else:
        member = await context.bot.get_chat_member(update.message.chat.id, user_id)
        is_admin = member.status in ["administrator", "creator"]
        
    if not is_admin:
        await update.message.reply_text("Ban khong co quyen su dung lenh nay.")
        return
        
    admin_text = """
HUONG DAN QUAN TRI (ADMIN/OWNER)

- !start : Reset toan bo no & Don dep nhom
- !clear [so] : Xoa tin nhan chat
- !exportno : Xuat file Excel nợ ca nhom
- !idgroups : Lay ID cac nhom dang dung (Private)
- !myid : Lay ID Telegram cua ban
- !allpaid @tagA @tagB : Tat toan no giua 2 nguoi (Admin)
"""
    await update.message.reply_text(admin_text)

async def no_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private": return
    group_id, user_id = update.message.chat.id, update.message.from_user.id
    tags = re.findall(r"@(\w+)", update.message.text)
    
    member_status = await context.bot.get_chat_member(group_id, user_id)
    is_admin = (user_id == OWNER_ID) or (member_status.status in ["administrator", "creator"])

    if len(tags) >= 2:
        u1_name, u2_name = tags[0], tags[1]
        u1_id, u2_id = find_user_id_by_username(u1_name), find_user_id_by_username(u2_name)
        if not u1_id or not u2_id:
            await update.message.reply_text("Khong tim thay du lieu 1 trong 2 nguoi.")
            return
        pair_debts, _ = calculate_group_debts(group_id)
        key = tuple(sorted((u1_id, u2_id)))
        amount = pair_debts.get(key, 0)
        if u1_id > u2_id: amount = -amount
        if amount == 0: await update.message.reply_text(f"@{u1_name} va @{u2_name} dang hoa nhau.")
        elif amount > 0: await update.message.reply_text(f"@{u2_name} dang no @{u1_name}: {format_currency(amount)}")
        else: await update.message.reply_text(f"@{u1_name} dang no @{u2_name}: {format_currency(abs(amount))}")
        return

    if len(tags) == 1 and is_admin:
        t_id = find_user_id_by_username(tags[0])
        if not t_id: return
        owe_them, they_owe = get_my_debts(t_id, group_id)
        res = f"📊 **DANH SÁCH NỢ CỦA @{tags[0].upper()}**\n\n"
        has = False
        for i in they_owe: res += f"• {tags[0]} nợ **{i['name']}**: `{format_currency(i['amount'])}`\n"; has = True
        for i in owe_them: res += f"• **{i['name']}** nợ {tags[0]}: `{format_currency(i['amount'])}`\n"; has = True
        if not has: res = f"✅ **@{tags[0]}** hiện không có nợ."
        await update.message.reply_text(res, parse_mode="Markdown"); return

    if context.args and context.args[0] == "all":
        pair_debts, user_names = calculate_group_debts(group_id)
        if not pair_debts:
            await update.message.reply_text("Nhom hien khong co no.")
            return
        res = "📋 **TỔNG HỢP CÔNG NỢ TOÀN NHÓM**\n\n"
        index = 1
        for (u1, u2), amount in pair_debts.items():
            if amount == 0: continue
            n1, n2 = user_names.get(u1, f"User {u1}"), user_names.get(u2, f"User {u2}")
            if amount > 0: res += f"{index}. **{n2}** nợ **{n1}**: `{format_currency(amount)}`\n"
            else: res += f"{index}. **{n1}** nợ **{n2}**: `{format_currency(abs(amount))}`\n"
            index += 1
        await update.message.reply_text(res, parse_mode="Markdown")
    else:
        owe_them, they_owe = get_my_debts(user_id, group_id)
        user_display = update.message.from_user.full_name or update.message.from_user.username
        title = f"📊 **DANH SÁCH NỢ CỦA BẠN ({user_display.upper()})**\n\n"
        res = ""
        for i in they_owe: res += f"• Bạn đang nợ **{i['name']}**: `{format_currency(i['amount'])}`\n"
        for i in owe_them: res += f"• **{i['name']}** đang nợ bạn: `{format_currency(i['amount'])}`\n"
        
        if not res:
            res = f"✅ Hiện tại **{user_display}** không có nợ nào."
        else:
            res = title + res
        await update.message.reply_text(res, parse_mode="Markdown")

async def lichsu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private":
        await update.message.reply_text("❌ Lệnh này chỉ khả dụng trong Group chat.")
        return
    txs = get_debts_in_group(update.message.chat.id)
    user_id = update.message.from_user.id
    target_username = context.args[0].replace("@", "") if context.args else None

    if target_username:
        filtered_txs = []
        last_settled_id = 0
        for t in txs:
            if "[TẤT TOÁN]" in t['reason']:
                is_me = (t['creditor_id'] == user_id or t['debtor_id'] == user_id)
                is_target = (t['creditor_name'].lower() == target_username.lower() or t['debtor_name'].lower() == target_username.lower())
                if is_me and is_target:
                    last_settled_id = max(last_settled_id, t['id'])
        
        for t in txs:
            is_me = (t['creditor_id'] == user_id or t['debtor_id'] == user_id)
            is_target = (t['creditor_name'].lower() == target_username.lower() or t['debtor_name'].lower() == target_username.lower())
            if is_me and is_target and t['id'] >= last_settled_id:
                filtered_txs.append(t)
                
        my_txs = sorted(filtered_txs, key=lambda x: x['id'], reverse=True)[:20]
        user_display = update.message.from_user.full_name or update.message.from_user.username
        title = f"📜 **LỊCH SỬ NỢ GIỮA {user_display.upper()} VÀ @{target_username.upper()}**\n\n"
    else:
        peers_last_settled = {}
        my_raw_txs = [t for t in txs if t['creditor_id'] == user_id or t['debtor_id'] == user_id]
        for t in my_raw_txs:
            if "[TẤT TOÁN]" in t['reason']:
                peer = t['creditor_name'] if t['debtor_id'] == user_id else t['debtor_name']
                peers_last_settled[peer.lower()] = max(peers_last_settled.get(peer.lower(), 0), t['id'])
        
        filtered_txs = []
        for t in my_raw_txs:
            peer = t['creditor_name'] if t['debtor_id'] == user_id else t['debtor_name']
            if t['id'] >= peers_last_settled.get(peer.lower(), 0):
                filtered_txs.append(t)

        limit = 50 if (context.args and context.args[0] == "all") else 15
        my_txs = sorted(filtered_txs, key=lambda x: x['id'], reverse=True)[:limit]
        user_display = update.message.from_user.full_name or update.message.from_user.username
        title = f"📜 **LỊCH SỬ GIAO DỊCH CỦA BẠN ({user_display.upper()})**\n\n"

    if not my_txs:
        await update.message.reply_text("Không tìm thấy dữ liệu lịch sử.")
        return

    res = title
    for t in my_txs:
        date_str = t['created_at'].split(".")[0] if isinstance(t['created_at'], str) else t['created_at'].strftime("%Y-%m-%d %H:%M")
        creator_name = "Chủ nợ" if t['created_by'] == t['creditor_id'] else "Người nợ"
        if t['created_by'] not in [t['creditor_id'], t['debtor_id']]:
            creator_name = "Admin/Khác"
        res += f"ID: {t['id']} | **{t['debtor_name']}** no **{t['creditor_name']}**: {format_currency(t['amount'])}\n"
        res += f"Ly do: {t['reason']}\n"
        res += f"{date_str} (Boi: {creator_name})\n\n"
    
    await update.message.reply_text(res, parse_mode="Markdown")

async def undo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private":
        await update.message.reply_text("❌ Lệnh này chỉ khả dụng trong Group chat.")
        return

    group_id = update.message.chat.id
    user_id = update.message.from_user.id
    
    if update.message.reply_to_message:
        replied_msg_id = update.message.reply_to_message.message_id
        txs = get_debts_in_group(group_id)
        target_tx = next((t for t in txs if t['message_id'] == replied_msg_id), None)
        
        if not target_tx:
            await update.message.reply_text("Khong tim thay giao dich lien quan den tin nhan nay.")
            return
            
        if target_tx['created_by'] != user_id:
            await update.message.reply_text("Ban chi co the hoan tac don no do chinh ban tao.")
            return
            
        if delete_transaction(target_tx['id'], user_id):
            await update.message.reply_text(f"HOAN TAC THANH CONG: Da xoa don ID {target_tx['id']} ({format_currency(target_tx['amount'])})")
        return

    txs = get_debts_in_group(group_id)
    my_last_tx = None
    for t in sorted(txs, key=lambda x: x['id'], reverse=True):
        if t['created_by'] == user_id:
            my_last_tx = t
            break
            
    if not my_last_tx:
        await update.message.reply_text("Bạn chưa tạo giao dịch nào gần đây để hoàn tác.")
        return
        
    if delete_transaction(my_last_tx['id'], user_id):
        msg = f"HOAN TAC THANH CONG\n"
        msg += f"Da xoa don: {my_last_tx['id']}\n"
        msg += f"Noi dung: {my_last_tx['debtor_name']} no {my_last_tx['creditor_name']} ({format_currency(my_last_tx['amount'])})\n"
        msg += f"Ly do: {my_last_tx['reason']}"
        await update.message.reply_text(msg)

async def nhacno_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private":
        await update.message.reply_text("❌ Lệnh này chỉ khả dụng trong Group chat.")
        return
    group_id = update.message.chat.id
    user_id = update.message.from_user.id
    user_name = update.message.from_user.full_name or update.message.from_user.username
    owe_me, _ = get_my_debts(user_id, group_id)
    
    if not owe_me:
        await update.message.reply_text("✅ Tuyệt vời! Hiện tại không có ai nợ bạn.")
        return
        
    res = f"📢 **THÔNG BÁO NHẮC NỢ TỪ {user_name}**\n\n"
    for item in owe_me:
        res += f"• @{item['name']} đang nợ: **{format_currency(item['amount'])}**\n"
    res += "\n💡 _Vui lòng nhắn tin riêng hoặc chuyển khoản để xóa nợ!_"
    await update.message.reply_text(res, parse_mode="Markdown")

async def allpaid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private":
        await update.message.reply_text("❌ Lệnh này chỉ khả dụng trong Group chat.")
        return
    tags = re.findall(r"@(\w+)", update.message.text)
    if not tags:
        await update.message.reply_text("Vui lòng tag người nợ.", parse_mode="Markdown")
        return
        
    group_id, user_id = update.message.chat.id, update.message.from_user.id
    member_status = await context.bot.get_chat_member(group_id, user_id)
    is_admin = (user_id == OWNER_ID) or (member_status.status in ["administrator", "creator"])

    if len(tags) >= 2:
        if not is_admin:
            await update.message.reply_text("❌ Ban khong co quyen tat toan no cho nguoi khac.")
            return
        u1_name, u2_name = tags[0], tags[1]
        u1_id, u2_id = find_user_id_by_username(u1_name), find_user_id_by_username(u2_name)
        if not u1_id or not u2_id:
            await update.message.reply_text("❌ Khong tim thay du lieu.")
            return
        pair_debts, user_names = calculate_group_debts(group_id)
        ids = sorted([u1_id, u2_id]); key = (ids[0], ids[1])
        net_amount = pair_debts.get(key, 0)
        if net_amount == 0:
            await update.message.reply_text(f"✅ @{u1_name} va @{u2_name} khong co no nhau.")
            return
        if net_amount > 0:
            debtor_id, debtor_name = ids[1], user_names.get(ids[1], u2_name)
            creditor_id, creditor_name = ids[0], user_names.get(ids[0], u1_name)
            amount = net_amount
        else:
            debtor_id, debtor_name = ids[0], user_names.get(ids[0], u1_name)
            creditor_id, creditor_name = ids[1], user_names.get(ids[1], u2_name)
            amount = abs(net_amount)

        save_transaction(group_id, {"id": debtor_id, "name": debtor_name}, {"id": creditor_id, "name": creditor_name},
                         amount, f"[ADMIN TẤT TOÁN] @{u1_name} & @{u2_name}", update.message.text, user_id, update.message.message_id)
        await update.message.reply_text(f"✅ [ADMIN] Đã tất toán giữa @{u1_name} và @{u2_name}.")
        return

    target_username = tags[0]
    target_id = find_user_id_by_username(target_username)
    if target_id is None:
        await update.message.reply_text("❌ Không tìm thấy dữ liệu.")
        return

    pair_debts, _ = calculate_group_debts(group_id)
    ids = sorted([user_id, target_id]); key = (ids[0], ids[1])
    net_amount = pair_debts.get(key, 0)
    debt_to_me = net_amount if user_id == ids[0] else -net_amount
    if debt_to_me <= 0:
        await update.message.reply_text(f"@{target_username} khong no ban.")
        return

    save_transaction(group_id, {"id": target_id, "name": target_username}, {"id": user_id, "name": update.message.from_user.full_name},
                     debt_to_me, f"[TẤT TOÁN] @{target_username}", update.message.text, user_id, update.message.message_id)
    await update.message.reply_text(f"✅ Đã tất toán! @{target_username} trả {format_currency(debt_to_me)}.")

async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    txs = get_debts_in_group(update.message.chat.id)
    my_txs = [t for t in txs if t['creditor_id'] == user_id or t['debtor_id'] == user_id]
    if not my_txs:
        await update.message.reply_text("Không có dữ liệu.")
        return
    wb = Workbook(); ws = wb.active; ws.title = "Lich Su No"
    ws.append(["ID", "Thời Gian", "Người Cho Nợ", "Người Nợ", "Số Tiền", "Lý Do"])
    for cell in ws[1]: cell.font = Font(bold=True)
    for t in my_txs:
        date_str = t['created_at'].split(".")[0] if isinstance(t['created_at'], str) else t['created_at'].strftime("%Y-%m-%d %H:%M")
        ws.append([t['id'], date_str, t['creditor_name'], t['debtor_name'], t['amount'], t['reason']])
    byte_io = io.BytesIO(); wb.save(byte_io); byte_io.seek(0); byte_io.name = "lich_su_no.xlsx"
    await update.message.reply_document(document=byte_io, caption="📊 File Excel lịch sử nợ.")

async def exportno_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = update.message.chat.id
    pair_debts, user_names = calculate_group_debts(group_id)
    actual_debts = {k: v for k, v in pair_debts.items() if v != 0}
    if not actual_debts:
        await update.message.reply_text("Nhom hien tai khong co no.")
        return
    wb = Workbook(); ws = wb.active; ws.title = "Tong Hop No"
    ws.append(["STT", "Người Nợ", "Người Cho Nợ", "Số Tiền Nợ"])
    for cell in ws[1]: cell.font = Font(bold=True)
    index = 1
    for (u1, u2), amount in actual_debts.items():
        n1, n2 = user_names.get(u1, f"User {u1}"), user_names.get(u2, f"User {u2}")
        if amount > 0: ws.append([index, n2, n1, amount])
        else: ws.append([index, n1, n2, abs(amount)])
        index += 1
    byte_io = io.BytesIO(); wb.save(byte_io); byte_io.seek(0); byte_io.name = "tong_hop_no.xlsx"
    await update.message.reply_document(document=byte_io, caption="📋 Bản tóm tắt công nợ.")

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ Lệnh này dành cho Chủ nhân!")
        return
    amount = int(context.args[0]) if context.args else 10
    if amount > 100: amount = 100
    chat_id, message_id = update.message.chat.id, update.message.message_id
    await context.bot.delete_message(chat_id, message_id)
    deleted = 0
    for i in range(1, amount + 1):
        try:
            await context.bot.delete_message(chat_id, message_id - i)
            deleted += 1
        except: continue
    info_msg = await context.bot.send_message(chat_id, f"🧹 Đã dọn dẹp {deleted} tin nhắn!")
    await asyncio.sleep(3)
    await context.bot.delete_message(chat_id, info_msg.message_id)
