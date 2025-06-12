import time
import json
import os
import requests
from collections import Counter
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = "8104621483:AAFn-qtWY-G2yQLGrZvZtFsYhmP0k4CpMAI"
ACCESS_TOKEN = "05%2F7JlwSPGwB1fKzi7qXLCUfxG%2F%2FwnP9B3UwDAmuWFLx4HmwqXGCmY2f%2BwVswnATdeJ1hnJUb8JEaXWr%2Bkf3SYji9zW1F5urA9fmlQia331SqlIQmeUS94Mz3ywCtmnj6ssOz4%2BcY91MtHQ1Z5Mchw0tGuI2SZx20zkVqWxbmMPbd8p3UyVQkYqPwgCPexrDhln59UbKBB2akAHlUFDedlcZ0jCROET21tYzOiNB1L36Uz6bWusDsxinaPChHhj4tJokZnWu8NeeDGXWLSeSr%2F00etslH1TXwCrs%2BrD4Dj%2B3OmJ3VlTStVXCEQLMwKvrMdILytS%2FBIYsfAZW%2BMDKlbHbfSbhlyb2jrYRX7ekIiTrO%2BYBr3m%2FKPMS79IxrWixb3geXzgczyY%3D.e90dcc10d9f881cd1b07d25587d93980e2c03e9207a35888e6da3500abcb5fbb" 
API_URL = "https://taixiu.backend-sunvn30.online/api/luckydice/GetSoiCau"
ADMIN_ID = 6925198778

def load_json(filename, default):
    if not os.path.exists(filename):
        return default
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def is_admin(user_id):
    return user_id == ADMIN_ID

def is_allowed(user_id):
    users = load_json("users.json", [])
    return user_id in users

def get_bot_status():
    status = load_json("status.json", {"active": True})
    return status.get("active", True)

def set_bot_status(state: bool):
    save_json("status.json", {"active": state})

def get_data():
    try:
        params = {"access_token": ACCESS_TOKEN} if ACCESS_TOKEN else {}
        res = requests.get(API_URL, params=params, timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"[ERROR] API request failed: {e}")
        return []

def dice_to_taixiu(total):
    return "Tài" if total >= 11 else "Xỉu"

def tim_cau_du_doan(lich_su, do_dai_cau=6):
    pattern = lich_su[-do_dai_cau:]
    past = lich_su[:-do_dai_cau]
    xuat_hien = [
        past[i + do_dai_cau]
        for i in range(len(past) - do_dai_cau + 1)
        if past[i:i + do_dai_cau] == pattern
    ]
    if not xuat_hien:
        return None, 0.0
    dem = Counter(xuat_hien)
    du_doan, cnt = dem.most_common(1)[0]
    ti_le = cnt / len(xuat_hien) * 100
    return du_doan, round(ti_le, 2)

def is_cau_1_1(lich_su, do_dai=6):
    if len(lich_su) < do_dai:
        return False
    pattern = lich_su[-do_dai:]
    return all(pattern[i] != pattern[i + 1] for i in range(len(pattern) - 1))

async def soicau(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not get_bot_status():
        await update.message.reply_text("❌ Bot đang bị tắt bởi Admin.")
        return
    if not is_allowed(user_id):
        await update.message.reply_text("🚫 Bạn chưa được cấp quyền sử dụng bot.")
        return

    await update.message.reply_text("🤖 Đang soi cầu từ 77 ván gần nhất...")

    attempts = 0
    while attempts < 10:
        data = get_data()
        if len(data) >= 78:
            lich_su = [dice_to_taixiu(item["DiceSum"]) for item in data[1:78]]
            last_session_id = data[0]["SessionId"]
            break
        attempts += 1
        await update.message.reply_text(f"⏳ Chờ dữ liệu đủ 77 ván... (lần {attempts})")
        time.sleep(2)
    else:
        await update.message.reply_text("❌ Không tải đủ dữ liệu sau 10 lần, thử lại sau.")
        return

    # Phân tích cầu
    du_doan_van_moi, ti_le = None, 0
    if is_cau_1_1(lich_su, do_dai=6):
        du_doan_van_moi = "Tài" if lich_su[-1] == "Xỉu" else "Xỉu"
        ti_le = 70
    else:
        for do_dai in range(6, 2, -1):
            du_doan, tl = tim_cau_du_doan(lich_su, do_dai)
            if du_doan and tl >= 60:
                du_doan_van_moi, ti_le = du_doan, tl
                break

    if not du_doan_van_moi:
        du_doan_van_moi, ti_le = "Xỉu", 50

    ls_10 = ' - '.join(lich_su[-10:])
    await update.message.reply_text(
        f"🎯 Dự đoán ván tiếp theo ({last_session_id + 1}): *{du_doan_van_moi}* (tỉ lệ {ti_le}%)\n"
        f"📉 Lịch sử 10 ván gần nhất:\n`{ls_10}`",
        parse_mode='Markdown'
    )
    await update.message.reply_text("⏳ Đang chờ kết quả ván mới...")

    # Chờ kết quả
    while True:
        time.sleep(4)
        data_moi = get_data()
        if not data_moi:
            continue
        current_id = data_moi[0]["SessionId"]
        if current_id != last_session_id:
            ket_qua = dice_to_taixiu(data_moi[0]["DiceSum"])
            kq = "✅ THẮNG!" if ket_qua == du_doan_van_moi else "❌ THUA!"
            await update.message.reply_text(
                f"✅ Ván {current_id} kết thúc!\n"
                f"Kết quả: *{ket_qua}*\n"
                f"Dự đoán: *{du_doan_van_moi}*\n"
                f"🎲 {kq}",
                parse_mode='Markdown'
            )
            break

# Các lệnh quản lý quyền và trạng thái

async def capquyen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 Bạn không có quyền dùng lệnh này.")
        return
    if not context.args:
        await update.message.reply_text("❗ /capquyen <user_id>")
        return
    uid = int(context.args[0])
    users = load_json("users.json", [])
    if uid in users:
        await update.message.reply_text("⚠️ ID này đã có quyền.")
    else:
        users.append(uid)
        save_json("users.json", users)
        await update.message.reply_text(f"✅ Đã cấp quyền cho ID: {uid}")

async def xoaquyen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 Bạn không có quyền dùng lệnh này.")
        return
    if not context.args:
        await update.message.reply_text("❗ /xoaquyen <user_id>")
        return
    uid = int(context.args[0])
    users = load_json("users.json", [])
    if uid in users:
        users.remove(uid)
        save_json("users.json", users)
        await update.message.reply_text(f"🗑️ Đã xóa quyền ID: {uid}")
    else:
        await update.message.reply_text("⚠️ ID không tồn tại.")

async def danhsachquyen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    users = load_json("users.json", [])
    if users:
        await update.message.reply_text("📜 Danh sách quyền:\n" + "\n".join(map(str, users)))
    else:
        await update.message.reply_text("❌ Chưa có ai được cấp quyền.")

async def bat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    set_bot_status(True)
    await update.message.reply_text("✅ Bot đã bật")

async def tat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    set_bot_status(False)
    await update.message.reply_text("🛑 Bot đã tắt")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("soicau", soicau))
    app.add_handler(CommandHandler("capquyen", capquyen))
    app.add_handler(CommandHandler("xoaquyen", xoaquyen))
    app.add_handler(CommandHandler("danhsachquyen", danhsachquyen))
    app.add_handler(CommandHandler("bat", bat))
    app.add_handler(CommandHandler("tat", tat))

    print("🤖 BOT ĐANG CHẠY TRỰC TUYẾN TRÊN TELEGRAM...")
    app.run_polling()

if __name__ == "__main__":
    main()
