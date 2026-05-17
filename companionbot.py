import os
import threading
import sqlite3
from flask import Flask
import telebot
from telebot import types

# Web Server (Render uchun)
app = Flask('')

@app.route('/')
def home():
    return "Anonim Chat va Dinamik Admin Bot Faol!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Token va Kalitlar
TOKEN = os.environ.get("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

# ADMIN ID (Bu yerga o'zingizning Telegram raqamingiz ID sini yozing!)
ADMIN_ID = 7180864511  # <--- O'ZINGIZNING ID'NGIZNI YOZING

# 💾 BAZA BILAN ISHLASH (SQLite)
DB_FILE = "chat_bot.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Foydalanuvchilar jadvali
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        name TEXT,
        age INTEGER,
        status TEXT DEFAULT 'start', 
        partner_id INTEGER DEFAULT 0
    )''')
    # Shikoyatlar jadvali
    cursor.execute('''CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_id INTEGER,
        target_id INTEGER,
        reason TEXT
    )''')
    # Sozlamalar jadvali (Kanalni saqlash uchun)
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    # Standart sozlamani kiritish (Boshida kanal majburiy emas - 'none')
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('mandatory_channel', 'none')")
    conn.commit()
    conn.close()

init_db()

# 🔑 Majburiy azolikni tekshirish xizmati (Bazadan o'qiydi)
def check_sub(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key='mandatory_channel'")
    channel = cursor.fetchone()[0]
    conn.close()
    
    if channel == "none" or not channel:
        return True  # Kanal o'chirilgan bo'lsa, hammani o'tkazadi
        
    try:
        status = bot.get_chat_member(channel, user_id).status
        if status in ['member', 'creator', 'administrator']:
            return True
        return False
    except Exception:
        return True  # Kanal topilmasa yoki xato bo'lsa o'tkazib yuboradi

# 🛠️ KLAVIATURALAR TIZIMI
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🔍 Suhbatdosh izlash 🚀", "👥 Onlayn a'zolar")
    markup.row("⚙️ Profilni tahrirlash")
    return markup

def chat_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("⏭ Keyingisi (O'tkazib yuborish)", "🛑 Suhbatni yakunlash")
    markup.row("🚨 Shikoyat qilish")
    return markup

def admin_menu():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key='mandatory_channel'")
    current_channel = cursor.fetchone()[0]
    conn.close()
    
    ch_text = "O'chirilgan ❌" if current_channel == "none" else current_channel
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📢 Xabar yuborish", callback_data="adm_broadcast"))
    markup.add(types.InlineKeyboardButton(f"📢 Kanal: {ch_text}", callback_data="adm_channel_setup"))
    markup.add(types.InlineKeyboardButton("📂 Shikoyatlarni ko'rish", callback_data="adm_reports"))
    markup.add(types.InlineKeyboardButton("👥 Foydalanuvchilar ro'yxati", callback_data="adm_users"))
    return markup

# 🚀 /start BUYRUG'I
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    if not check_sub(user_id):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key='mandatory_channel'")
        channel = cursor.fetchone()[0]
        conn.close()
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Kanalga a'zo bo'lish ➕", url=f"https://t.me/{channel.replace('@','') }"))
        bot.send_message(user_id, f"⚠️ Botdan foydalanish uchun hamkor kanalimizga a'zo bo'lishingiz shart:\n\nA'zo bo'lib, qayta /start buyrug'ini bosing.", reply_markup=markup)
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.execute("INSERT INTO users (user_id, status) VALUES (?, 'reg_name')", (user_id,))
        conn.commit()
        bot.send_message(user_id, "👋 Salom! Anonim chatga xush kelibsiz.\n\nSuhbatni boshlashdan oldin ro'yxatdan o'tamiz. **Ismingizni kiriting:**", parse_mode="Markdown")
    else:
        cursor.execute("UPDATE users SET status='registered', partner_id=0 WHERE user_id=?", (user_id,))
        conn.commit()
        bot.send_message(user_id, "Asosiy menyuga qaytdingiz ✨", reply_markup=main_menu())
    conn.close()

# 🎛 /admin BUYRUG'I
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(ADMIN_ID, "💻 **Admin boshqaruv paneli:**", parse_mode="Markdown", reply_markup=admin_menu())

# 📝 XABARLARNI BOSHQARISH
@bot.message_handler(content_types=['text', 'photo'])
def handle_all(message):
    user_id = message.from_user.id
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT status, partner_id, name FROM users WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    
    if not res:
        conn.close()
        return

    status, partner_id, name = res

    # 1. Ro'yxatdan o'tish jarayonlari
    if status == 'reg_name':
        cursor.execute("UPDATE users SET name=?, status='reg_age' WHERE user_id=?", (message.text, user_id))
        conn.commit()
        bot.send_message(user_id, "Yoshingizni kiriting (Faqat raqamda):")
        conn.close()
        return
        
    elif status == 'reg_age':
        if not message.text.isdigit():
            bot.send_message(user_id, "Iltimos, yoshingizni to'g'ri raqamda kiriting:")
            conn.close()
            return
        cursor.execute("UPDATE users SET age=?, status='registered' WHERE user_id=?", (int(message.text), user_id))
        conn.commit()
        bot.send_message(user_id, "🎉 Ro'yxatdan muvaffaqiyatli o'tdingiz!", reply_markup=main_menu())
        conn.close()
        return

    # Admin xabar yuborish holati
    if status == 'adm_waiting_msg' and user_id == ADMIN_ID:
        cursor.execute("SELECT user_id FROM users")
        all_users = cursor.fetchall()
        for u in all_users:
            try:
                bot.send_message(u[0], f"📢 **Admin xabari:**\n\n{message.text}", parse_mode="Markdown")
            except:
                continue
        cursor.execute("UPDATE users SET status='registered' WHERE user_id=?", (ADMIN_ID,))
        conn.commit()
        bot.send_message(ADMIN_ID, "Xabar barcha foydalanuvchilarga yuborildi!", reply_markup=main_menu())
        conn.close()
        return

    # Admin yangi kanal sozlash holati
    if status == 'adm_waiting_channel' and user_id == ADMIN_ID:
        new_ch = message.text.strip()
        if new_ch.lower() == "o'chirish" or new_ch.lower() == "ochirish":
            cursor.execute("UPDATE settings SET value='none' WHERE key='mandatory_channel'")
            bot.send_message(ADMIN_ID, "🛑 Majburiy kanal a'zoligi muvaffaqiyatli o'chirildi!")
        else:
            if not new_ch.startswith("@"):
                new_ch = "@" + new_ch
            cursor.execute("UPDATE settings SET value=? WHERE key='mandatory_channel'", (new_ch,))
            bot.send_message(ADMIN_ID, f"✅ Yangi majburiy kanal o'rnatildi: {new_ch}\n\n⚠️ Bot ushbu kanalda **Admin** bo'lishi shart!")
        
        cursor.execute("UPDATE users SET status='registered' WHERE user_id=?", (ADMIN_ID,))
        conn.commit()
        conn.close()
        return

    # 2. Asosiy Menyudagi amallar
    if status == 'registered':
        if message.text == "🔍 Suhbatdosh izlash 🚀":
            bot.send_message(user_id, "⏳ Mos keladigan faol suhbatdosh qidirilmoqda...", reply_markup=types.ReplyKeyboardRemove())
            
            cursor.execute("SELECT user_id FROM users WHERE status='searching' AND user_id!=?", (user_id,))
            partner = cursor.fetchone()
            
            if partner:
                p_id = partner[0]
                cursor.execute("UPDATE users SET status='chatting', partner_id=? WHERE user_id=?", (p_id, user_id))
                cursor.execute("UPDATE users SET status='chatting', partner_id=? WHERE user_id=?", (user_id, p_id))
                conn.commit()
                
                bot.send_message(user_id, "🎉 Suhbatdosh topildi! Salomlashishingiz mumkin.", reply_markup=chat_menu())
                bot.send_message(p_id, "🎉 Suhbatdosh topildi! Salomlashishingiz mumkin.", reply_markup=chat_menu())
            else:
                cursor.execute("UPDATE users SET status='searching' WHERE user_id=?", (user_id,))
                conn.commit()
                
        elif message.text == "👥 Onlayn a'zolar":
            cursor.execute("SELECT COUNT(*) FROM users WHERE status='chatting' OR status='searching'")
            online_count = cursor.fetchone()[0]
            bot.send_message(user_id, f"🟢 Hozirda botda {online_count + 2} ta faol foydalanuvchi suhbatda!")
            
        elif message.text == "⚙️ Profilni tahrirlash":
            cursor.execute("UPDATE users SET status='reg_name' WHERE user_id=?", (user_id,))
            conn.commit()
            bot.send_message(user_id, "Ismingizni qaytadan kiriting:")

    # 3. Anonim chat ichidagi jarayonlar
    elif status == 'chatting':
        if message.text == "🛑 Suhbatni yakunlash":
            cursor.execute("UPDATE users SET status='registered', partner_id=0 WHERE user_id=?", (user_id,))
            cursor.execute("UPDATE users SET status='registered', partner_id=0 WHERE user_id=?", (partner_id,))
            conn.commit()
            bot.send_message(user_id, "Suhbat yakunlandi. 🚪", reply_markup=main_menu())
            bot.send_message(partner_id, "Suhbatdosh muloqotni yakunladi. 🚪", reply_markup=main_menu())
            
        elif message.text == "⏭ Keyingisi (O'tkazib yuborish)":
            cursor.execute("UPDATE users SET status='registered', partner_id=0 WHERE user_id=?", (user_id,))
            cursor.execute("UPDATE users SET status='registered', partner_id=0 WHERE user_id=?", (partner_id,))
            conn.commit()
            bot.send_message(partner_id, "Suhbatdosh suhbatni o'tkazib yubordi. ⏭", reply_markup=main_menu())
            
            cursor.execute("UPDATE users SET status='searching' WHERE user_id=?", (user_id,))
            conn.commit()
            bot.send_message(user_id, "⏳ Yangi suhbatdosh qidirilmoqda...")
            
            cursor.execute("SELECT user_id FROM users WHERE status='searching' AND user_id!=?", (user_id,))
            new_partner = cursor.fetchone()
            if new_partner:
                np_id = new_partner[0]
                cursor.execute("UPDATE users SET status='chatting', partner_id=? WHERE user_id=?", (np_id, user_id))
                cursor.execute("UPDATE users SET status='chatting', partner_id=? WHERE user_id=?", (user_id, np_id))
                conn.commit()
                bot.send_message(user_id, "🎉 Yangi suhbatdosh topildi!", reply_markup=chat_menu())
                bot.send_message(np_id, "🎉 Yangi suhbatdosh topildi!", reply_markup=chat_menu())
                
        elif message.text == "🚨 Shikoyat qilish":
            cursor.execute("INSERT INTO reports (from_id, target_id, reason) VALUES (?, ?, ?)", (user_id, partner_id, "Nojo'ya xatti-harakat"))
            conn.commit()
            bot.send_message(user_id, "Shikoyatingiz qabul qilindi. 👮‍♂️")
            bot.send_message(ADMIN_ID, f"🚨 **Yangi Shikoyat:**\nKimdan: ID {user_id}\nKimning ustidan: ID {partner_id}")
            
        else:
            if message.content_type == 'text':
                bot.send_message(partner_id, message.text)
            elif message.content_type == 'photo':
                bot.send_photo(partner_id, message.photo[-1].file_id, caption=message.caption)

    conn.close()

# ⚙️ ADMIN CALLBACKAMALLARI
@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def admin_calls(call):
    if call.from_user.id != ADMIN_ID: return
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    if call.data == "adm_broadcast":
        cursor.execute("UPDATE users SET status='adm_waiting_msg' WHERE user_id=?", (ADMIN_ID,))
        conn.commit()
        bot.send_message(ADMIN_ID, "📢 Barcha foydalanuvchilarga yuboriladigan xabar matnini yozing:")
        
    elif call.data == "adm_channel_setup":
        cursor.execute("UPDATE users SET status='adm_waiting_channel' WHERE user_id=?", (ADMIN_ID,))
        conn.commit()
        bot.send_message(ADMIN_ID, "📝 Yangi majburiy kanal `username`ini yozib yuboring (Masalan: `@kinolar_olami`).\n\nAgar majburiy a'zolikni butunlay o'chirib qo'ymoqchi bo'lsangiz, shunchaki **`O'chirish`** deb yozib yuboring.")
        
    elif call.data == "adm_reports":
        cursor.execute("SELECT * FROM reports LIMIT 10")
        reps = cursor.fetchall()
        if not reps:
            bot.send_message(ADMIN_ID, "Hozircha shikoyatlar yo'q.")
        else:
            msg = "🚨 **Oxirgi shikoyatlar:**\n\n"
            for r in reps:
                msg += f"📌 ID: {r[0]} | Kimdan: {r[1]} ➡️ Kimning ustidan: {r[2]}\n"
            bot.send_message(ADMIN_ID, msg, parse_mode="Markdown")
            
    elif call.data == "adm_users":
        cursor.execute("SELECT user_id, name, age FROM users LIMIT 20")
        usrs = cursor.fetchall()
        msg = "👥 **Foydalanuvchilar ro'yxati (Bog'lanish uchun nomni bosing):**\n\n"
        for u in usrs:
            msg += f"👤 [{u[1]}](tg://user?id={u[0]}) | Yoshi: {u[2]} | ID: `{u[0]}`\n"
        bot.send_message(ADMIN_ID, msg, parse_mode="Markdown")
        
    conn.close()
    bot.answer_callback_query(call.id)

if __name__ == "__main__":
    t = threading.Thread(target=run_server)
    t.start()
    print("Dinamik Kanal va Anonim Chat tizimi muvaffaqiyatli yondi!")
    bot.infinity_polling()
