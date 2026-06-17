import os
import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ==================== CẤU HÌNH BẢO MẬT ====================
TOKEN = "8418289818:AAGRJP35i70scXBZi1AfMpvzS7IuTX3ZXmI"
OWNER_ID = 1087968824 # Thay bằng ID Telegram của bạn (lấy từ @userinfobot)
DB_FILE = "allowed_groups.txt"
SUDO_FILE = "sudo_users.txt"
# ==========================================================

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Trạng thái bật/tắt chửi mặc định của bot (True là đang bật)
bot_chat_enabled = True

# --- Quản lý dữ liệu file ---
def load_ids(filename):
    if not os.path.exists(filename):
        return set()
    with open(filename, "r") as f:
        return set(int(line.strip()) for line in f if line.strip())

def save_ids(filename, id_set):
    with open(filename, "w") as f:
        for _id in id_set:
            f.write(f"{_id}\n")

allowed_groups = load_ids(DB_FILE)
sudo_users = load_ids(SUDO_FILE)

# Kiểm tra quyền: Phải là Chủ sở hữu HOẶC người được cấp quyền Sudo thông qua /chophep
def has_permission(user_id):
    return user_id == OWNER_ID or user_id in sudo_users

def is_group_allowed(update: Update) -> bool:
    if not update.effective_chat:
        return False
    chat_id = update.effective_chat.id
    if update.effective_chat.type in ["group", "supergroup"]:
        return chat_id in allowed_groups
    return True

# --- 1. Giao diện lệnh /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("👤 Admin", url="https://t.me"),
            InlineKeyboardButton("📢 Channel", url="https://t.me")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text="👋 Chào mừng đến với Gs_bot", reply_markup=reply_markup)

# --- 2. Cấp/Hủy quyền bằng /chophep và /kochophep (Chỉ OWNER được dùng) ---
async def grant_permission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Bạn phải reply (phản hồi) tin nhắn của người muốn cho phép!")
        return
    
    target_id = update.message.reply_to_message.from_user.id
    target_name = update.message.reply_to_message.from_user.first_name
    
    sudo_users.add(target_id)
    save_ids(SUDO_FILE, sudo_users)
    await update.message.reply_text(f"✅ Đã cấp quyền điều khiển bot cho {target_name}. Người này có thể dùng /onchat và /offchat.")

async def revoke_permission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Bạn phải reply (phản hồi) tin nhắn của người muốn hủy cho phép!")
        return
    
    target_id = update.message.reply_to_message.from_user.id
    target_name = update.message.reply_to_message.from_user.first_name
    
    if target_id in sudo_users:
        sudo_users.remove(target_id)
        save_ids(SUDO_FILE, sudo_users)
        await update.message.reply_text(f"❌ Đã tước quyền điều khiển bot của {target_name}.")
    else:
        await update.message.reply_text(f"💡 Người này hiện tại vốn không có quyền điều khiển.")

# --- 3. Bật/Tắt chửi (/onchat, /offchat) (Owner & Người được /chophep được dùng) ---
async def on_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_chat_enabled
    if not has_permission(update.effective_user.id) or not is_group_allowed(update):
        return
    bot_chat_enabled = True
    await update.message.reply_text("🗣️ Chế độ bố láo đã BẬT. Sủa đi các em!")

async def off_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_chat_enabled
    if not has_permission(update.effective_user.id) or not is_group_allowed(update):
        return
    bot_chat_enabled = False
    await update.message.reply_text("🤫 Chế độ bố láo đã TẮT. Bot tạm thời đi ngủ.")

# --- 4. Quản lý nhóm (/add, /cc) (Owner & Người được /chophep được dùng) ---
async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not has_permission(update.effective_user.id):
        return
    chat_id = update.effective_chat.id
    if chat_id not in allowed_groups:
        allowed_groups.add(chat_id)
        save_ids(DB_FILE, allowed_groups)
        await update.message.reply_text("✅ Box này dùng được bot rồi đấy.")

async def remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not has_permission(update.effective_user.id):
        return
    chat_id = update.effective_chat.id
    if chat_id in allowed_groups:
        allowed_groups.remove(chat_id)
        save_ids(DB_FILE, allowed_groups)
        await update.message.reply_text("⚠️ Đã cấm box này sử dụng bot.")

# --- 5. Lệnh nâng/hạ Admin (/upadm, /sos) (Owner & Người được /chophep được dùng) ---
async def up_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not has_permission(update.effective_user.id) or not is_group_allowed(update):
        return
    if not update.message.reply_to_message:
        return

    target_user = update.message.reply_to_message.from_user
    try:
        await context.bot.promote_chat_member(
            chat_id=update.effective_chat.id, user_id=target_user.id,
            can_manage_chat=True, can_delete_messages=True, can_manage_video_chats=True,
            can_restrict_members=True, can_promote_members=False, can_change_info=True, can_invite_users=True
        )
        await update.message.reply_text(f"✅ Đã nâng Admin cho {target_user.mention_html()}.", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {e}")

async def down_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not has_permission(update.effective_user.id) or not is_group_allowed(update):
        return
    if not update.message.reply_to_message:
        return

    target_user = update.message.reply_to_message.from_user
    try:
        await context.bot.promote_chat_member(
            chat_id=update.effective_chat.id, user_id=target_user.id,
            can_manage_chat=False, can_delete_messages=False, can_manage_video_chats=False,
            can_restrict_members=False, can_promote_members=False, can_change_info=False, can_invite_users=False
        )
        await update.message.reply_text(f"⚠️ Đã hạ Admin của {target_user.mention_html()} xuống thành viên thường.", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {e}")

# --- 6. Kho từ vựng bố láo ---
async def reply_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_group_allowed(update) or not bot_chat_enabled:
        return

    text = update.message.text.lower()
    name = update.effective_user.first_name

    chao_responses = [
        f"Chào cái cc gì, rảnh háng à {name}?", f"Lại gặp thằng {name} này, mệt vcl.",
        "Sủa ít thôi, chào hỏi cl.", f"Hi cc, tag t làm gì đấy {name}?",
        "Lại một đứa vô tri chào hỏi, cút giùm.", "Chào cc gì mà chào, thích đấm nhau à?"
    ]

    bot_responses = [
        "Kêu t làm cái đb gì?", "T đang bận ngủ, cút!", "Gõ ít chữ thôi không bay màu giờ.",
        "Lại hỏi ngu cái gì nữa đúng không?", "Sủa nhanh đi t còn đi ngủ, mệt mỏi vcl.",
        "Gặp t là đen rồi con ạ, réo cl.", "Kêu clg? Có tiền thì nói chuyện không thì lượn."
    ]

    chui_responses = [
        "M chửi ai đấy thằng ranh con? Thích ăn sút ko?", "Dcm m thích war ko? T chấp cả lò nhà m.",
        "Nít ranh tinh tướng, clg cũng chửi được.", "Sủa tiếp đi t nghe, đúng là đồ tấu hài.",
        "Chửi thề cl, t vả rụng răng giờ.", "Gớm, mở mồm ra là dcm vcl, vô học thế con?"
    ]

    if any(keyword in text for keyword in ["chào", "hi", "hello"]):
        await update.message.reply_text(random.choice(chao_responses))
    elif "bot" in text:
        await update.message.reply_text(random.choice(bot_responses))
    elif any(keyword in text for keyword in ["cl", "cc", "vcl", "dcm", "đb", "ngu", "chửi", "đm"]):
        await update.message.reply_text(random.choice(chui_responses))
    else:
        if random.random() < 0.3:  # 30% tỷ lệ cà khịa ngẫu nhiên
            random_responses = [
                "Nói cái clg thế không biết?", "Nín giùm cái, đọc nhức cả mắt.",
                "T thấy m xàm vcl rồi đấy.", "Gớm, tinh tướng thế là cùng.",
                "Bớt sủa xàm đi con trai.", "Phát biểu câu nghe đần vcl."
            ]
            await update.message.reply_text(random.choice(random_responses))

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_group))
    app.add_handler(CommandHandler("cc", remove_group))
    app.add_handler(CommandHandler("upadm", up_admin))
    app.add_handler(CommandHandler("sos", down_admin))
    app.add_handler(CommandHandler("onchat", on_chat))
    app.add_handler(CommandHandler("offchat", off_chat))
    
    # Đăng ký 2 lệnh cấp/hủy quyền theo yêu cầu mới của bạn
    app.add_handler(CommandHandler("chophep", grant_permission))
    app.add_handler(CommandHandler("kochophep", revoke_permission))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_chat))

    print("Gs_bot phân quyền đang chạy...")
    app.run_polling()

if __name__ == '__main__':
    main()
