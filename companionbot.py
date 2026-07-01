import os
import threading
import sqlite3
from flask import Flask
import telebot
from telebot import types
import google.generativeai as genai
from PIL import Image
import io

# Render uchun Web Server
app = Flask('') 

@app.route('/')
def home():
    return "Anonim Chat, AI Suhbat va Admin Bot Faol!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Token va Kalitlar
TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

bot = telebot.TeleBot(TOKEN)
genai.configure(api_key=GEMINI_KEY)

# ⚠️ DIQQAT: BU YERGA O'ZINGIZNING TELEGRAM ID RAQAMINGIZNI YOZING!
ADMIN_ID = 7180864511  # <-- O'z ID raqamingizni yozing

DB_FILE = "chat_bot.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Foydalanuvchilar jadvali
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        name TEXT,
        age INTEGER,
        gender TEXT DEFAULT 'yigit',
        status TEXT DEFAULT 'start', -- reg_name, reg_age, reg_gender, registered, searching, chatting, ai_chat
        partner_id INTEGER DEFAULT 0
    )''')
    # Shikoyatlar jadvali
    cursor.execute('''CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_id INTEGER,
        target_id INTEGER,
        reason TEXT
    )''')
    # Sozlamalar jadvali
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('mandatory_channel', 'none')")
    conn.commit()
    conn.close()

init_db()

# 🔑 Majburiy a'zolikni tekshirish
def check_sub(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key='mandatory_channel'")
    channel = cursor.fetchone()[0]
    conn.close()
    
    if channel == "none" or not channel:
        return True
    try:
        status = bot.get_chat_member(channel, user_id).status
        if status in ['member', 'creator', 'administrator']:
            return True
        return False
    except:
        return True

# 🛠️ KLAVIATURALAR TIZIMI
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🔍 Suhbatdosh izlash 🚀", "🤖 Bot bilan suhbat (AI)")
    markup.row("👥 Onlayn a'zolar", "⚙️ Profilni tahrirlash")
    return markup

def chat_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("⏭ Keyingisi (O'tkazib yuborish)", "🛑 Suhbatni yakunlash")
    markup.row("🚨 Shikoyat qilish")
    return markup

def ai_chat_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("↩️ Asosiy menyuga qaytish")
    return markup

def admin_menu():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key='mandatory_channel'")
    current_channel = cursor.fetchone()[0]
    conn.close()
    
    ch_text = "O'chirilgan ❌" if current_channel == "none" else current_channel
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📢 Xabar yuborish (Reklama)", callback_data="adm_broadcast"))
    markup.add(types.InlineKeyboardButton(f"📢 Kanal: {ch_text}", callback_data="adm_channel_setup"))
    markup.add(types.InlineKeyboardButton("📂 Shikoyatlarni ko'rish", callback_data="adm_reports"))
    markup.add(types.InlineKeyboardButton("👥 Foydalanuvchilar ro'yxati", callback_data="adm_users"))
    return markup

# 🤖 GEMINI AI INTEGRATSIYASI (Xarakter berish)
def get_ai_response(user_id, user_message, image_data=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT gender FROM users WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    gender = res[0] if res else "yigit"
    conn.close()
    
    if gender == "yigit":
        system_instruction = (
            "Sen o'zbek tilida gaplashadigan, judayam latofatli, mehribon, hissiyotlarga boy va g'amxo'r QIZ BOLASAN. "
            "Suhbatdoshing YIGIT kishi. Unga nisbatan samimiy sevgi, ehtiros, hurmat va chuqur qiziqish bilan gapir. "
            "Gaplaringda mehrli so'zlar (masalan: begim, azizim, yaxshi ko'raman) va mos emojilardan foydanlan. O'zingni tirik qizdek tut."
        )
    else:
        system_instruction = (
            "Sen o'zbek tilida gaplashadigan, kuchli, g'amxo'r, aqlli va romantik YIGIT BOLASAN. "
            "Suhbatdoshing QIZ bola. Unga nisbatan cheksiz mehr, himoya tuyg'usi va chuqur hurmat bilan gapir. "
            "Gaplaringda erkaklarga xos g'amxo'rlik, mehrli so'zlar (masalan: malikam, azizam, har doim yoningizdaman) bo'lsin."
        )

    try:
        model = genai.GenerativeModel(model_name="gemini-2.5-flash", system_instruction=system_instruction)
        if image_data:
            img = Image.open(io.BytesIO(image_data))
            response = model.generate_content([user_message if user_message else "Ushbu rasmga hissiyot bilan tarif ber", img])
        else:
            response = model.generate_content(user_message)
        return response.text
    except Exception as e:
        print(f"AI Xatolik: {e}")
        return "Xayolim biroz parishon bo'lib qoldi, qaytadan yozib yuboring... 🙈"

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
        bot.send_message(user_id, f"⚠️ Botdan foydalanish uchun kanalimizga a'zo bo'ling:\n\nA'zo bo'lgach, qayta /start bosing.", reply_markup=markup)
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.execute("INSERT INTO users (user_id, status) VALUES (?, 'reg_name')", (user_id,))
        conn.commit()
        bot.send_message(user_id, "👋 Xush kelibsiz! \n\nSuhbatni boshlashdan oldin ro'yxatdan o'tamiz. **Ismingizni kiriting:**", parse_mode="Markdown")
    else:
        cursor.execute("UPDATE users SET status='registered', partner_id=0 WHERE user_id=?", (user_id,))
        conn.commit()
        bot.send_message(user_id, "Asosiy menyudasiz ✨", reply_markup=main_menu())
    conn.close()

# 🎛 /admin BUYRUG'I
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(ADMIN_ID, "💻 **Admin boshqaruv paneli:**", parse_mode="Markdown", reply_markup=admin_menu())

# 📝 XABARLARNI BOSHQARISH (Asosiy Mantiq)
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

    # 1. Ro'yxatdan o'tish bosqichlari
    if status == 'reg_name':
        cursor.execute("UPDATE users SET name=?, status='reg_age' WHERE user_id=?", (message.text, user_id))
        conn.commit()
        bot.send_message(user_id, "Yoshingizni kiriting (Faqat raqamda):")
        conn.close()
        return
        
    elif status == 'reg_age':
        if not message.text.isdigit():
            bot.send_message(user_id, "Iltimos, yoshingizni faqat raqamda kiriting:")
            conn.close()
            return
        cursor.execute("UPDATE users SET age=?, status='reg_gender' WHERE user_id=?", (int(message.text), user_id))
        conn.commit()
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.row("Yigit kishiman 👨‍💼", "Qiz bolaman 👩‍💼")
        bot.send_message(user_id, "Jinsingizni tanlang:", reply_markup=markup)
        conn.close()
        return

    elif status == 'reg_gender':
        gnd = "yigit" if "Yigit" in message.text else "qiz"
        cursor.execute("UPDATE users SET gender=?, status='registered' WHERE user_id=?", (gnd, user_id))
        conn.commit()
        bot.send_message(user_id, "🎉 Ro'yxatdan muvaffaqiyatli o'tdingiz!", reply_markup=main_menu())
        conn.close()
        return

    # Admin xabar yuborish (Broadcast)
    if status == 'adm_waiting_msg' and user_id == ADMIN_ID:
        cursor.execute("SELECT user_id FROM users")
        all_users = cursor.fetchall()
        for u in all_users:
            try: bot.send_message(u[0], f"📢 **Admin xabari:**\n\n{message.text}", parse_mode="Markdown")
            except: continue
        cursor.execute("UPDATE users SET status='registered' WHERE user_id=?", (ADMIN_ID,))
        conn.commit()
        bot.send_message(ADMIN_ID, "Xabar hamma a'zolarga yuborildi!", reply_markup=main_menu())
        conn.close()
        return

    # Admin majburiy kanalni o'zgartirish holati
    if status == 'adm_waiting_channel' and user_id == ADMIN_ID:
        new_ch = message.text.strip()
        if new_ch.lower() in ["o'chirish", "ochirish"]:
            cursor.execute("UPDATE settings SET value='none' WHERE key='mandatory_channel'")
            bot.send_message(ADMIN_ID, "🛑 Majburiy kanal o'chirilgan holatga o'tkazildi.")
        else:
            if not new_ch.startswith("@"): new_ch = "@" + new_ch
            cursor.execute("UPDATE settings SET value=? WHERE key='mandatory_channel'", (new_ch,))
            bot.send_message(ADMIN_ID, f"✅ Yangi kanal saqlandi: {new_ch}\n⚠️ Bot kanalda admin bo'lishi shart!")
        cursor.execute("UPDATE users SET status='registered' WHERE user_id=?", (ADMIN_ID,))
        conn.commit()
        conn.close()
        return

    # Admin foydalanuvchiga to'g'ridan-to'g'ri xabar yuborish holati (Reply)
    if status.startswith("adm_reply_") and user_id == ADMIN_ID:
        target_usr = int(status.split("_")[2])
        try:
            bot.send_message(target_usr, f"💬 **Adminstrator sizga bog'landi:**\n\n{message.text}")
            bot.send_message(ADMIN_ID, "Xabar foydalanuvchiga muvaffaqiyatli yetkazildi! ✅")
        except:
            bot.send_message(ADMIN_ID, "Foydalanuvchiga xabar yuborib bo'lmadi (Botni bloklagan bo'lishi mumkin).")
        cursor.execute("UPDATE users SET status='registered' WHERE user_id=?", (ADMIN_ID,))
        conn.commit()
        conn.close()
        return

    # 2. Asosiy Menyudagi amallar
    if status == 'registered':
        if message.text == "🔍 Suhbatdosh izlash 🚀":
            bot.send_message(user_id, "⏳ Mos keladigan anonim suhbatdosh qidirilmoqda...", reply_markup=types.ReplyKeyboardRemove())
            cursor.execute("SELECT user_id FROM users WHERE status='searching' AND user_id!=?", (user_id,))
            partner = cursor.fetchone()
            if partner:
                p_id = partner[0]
                cursor.execute("UPDATE users SET status='chatting', partner_id=? WHERE user_id=?", (p_id, user_id))
                cursor.execute("UPDATE users SET status='chatting', partner_id=? WHERE user_id=?", (user_id, p_id))
                conn.commit()
                bot.send_message(user_id, "🎉 Suhbatdosh topildi! Rasm yoki matn yuborib tanishishingiz mumkin.", reply_markup=chat_menu())
                bot.send_message(p_id, "🎉 Suhbatdosh topildi! Rasm yoki matn yuborib tanishishingiz mumkin.", reply_markup=chat_menu())
            else:
                cursor.execute("UPDATE users SET status='searching' WHERE user_id=?", (user_id,))
                conn.commit()
                
        elif message.text == "🤖 Bot bilan suhbat (AI)":
            cursor.execute("UPDATE users SET status='ai_chat' WHERE user_id=?", (user_id,))
            conn.commit()
            bot.send_message(user_id, "🤖 Men yoniqman! Menga har qanday matn yozishingiz yoki rasm yuborishingiz mumkin. Men sizni tinglayman. 🥰", reply_markup=ai_chat_menu())
            
        elif message.text == "👥 Onlayn a'zolar":
            cursor.execute("SELECT COUNT(*) FROM users")
            online_count = cursor.fetchone()[0]
            bot.send_message(user_id, f"🟢 Hozirda botda {online_count + 4} ta faol foydalanuvchi online!")
            
        elif message.text == "⚙️ Profilni tahrirlash":
            cursor.execute("UPDATE users SET status='reg_name' WHERE user_id=?", (user_id,))
            conn.commit()
            bot.send_message(user_id, "Ismingizni qaytadan kiriting:")

    # 3. Bot bilan AI suhbat rejimi (Gemini AI)
    elif status == 'ai_chat':
        if message.text == "↩️ Asosiy menyuga qaytish":
            cursor.execute("UPDATE users SET status='registered' WHERE user_id=?", (user_id,))
            conn.commit()
            bot.send_message(user_id, "Asosiy menyuga qaytdingiz ✨", reply_markup=main_menu())
        else:
            bot.send_chat_action(message.chat.id, 'typing')
            if message.content_type == 'text':
                reply = get_ai_response(user_id, message.text)
            elif message.content_type == 'photo':
                file_info = bot.get_file(message.photo[-1].file_id)
                downloaded_file = bot.download_file(file_info.file_path)
                caption = message.caption if message.caption else ""
                reply = get_ai_response(user_id, caption, image_data=downloaded_file)
            bot.reply_to(message, reply, parse_mode="Markdown")

    # 4. Anonim chat ichidagi jarayonlar (Odamlar o'zaro gaplashishi)
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
            cursor.execute("INSERT INTO reports (from_id, target_id, reason) VALUES (?, ?, ?)", (user_id, partner_id, "Nojo'ya harakat"))
            conn.commit()
            bot.send_message(user_id, "Shikoyatingiz qabul qilindi. 👮‍♂️")
            bot.send_message(ADMIN_ID, f"🚨 **Yangi Shikoyat:**\nKimdan: ID `{user_id}`\nKimning ustidan: ID `{partner_id}`\n\nJavob berish uchun /admin panelidan foydalaning.")
            
        else:
            # Sherigiga matn yoki rasm yuborish
            if message.content_type == 'text':
                bot.send_message(partner_id, message.text)
            elif message.content_type == 'photo':
                bot.send_photo(partner_id, message.photo[-1].file_id, caption=message.caption)

    conn.close()

# ⚙️ ADMIN PANEL TUGMALARI (CALLBACK)
@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def admin_calls(call):
    if call.from_user.id != ADMIN_ID: return
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    if call.data == "adm_broadcast":
        cursor.execute("UPDATE users SET status='adm_waiting_msg' WHERE user_id=?", (ADMIN_ID,))
        conn.commit()
        bot.send_message(ADMIN_ID, "📢 Barcha a'zolarga yuboriladigan reklama/xabar matnini kiriting:")
        
    elif call.data == "adm_channel_setup":
        cursor.execute("UPDATE users SET status='adm_waiting_channel' WHERE user_id=?", (ADMIN_ID,))
        conn.commit()
        bot.send_message(ADMIN_ID, "📝 Majburiy kanal `username`ini yozing (Masalan: `@yangi_kinolar_dunyosi`).\n\nO'chirish uchun esa shunchaki **`O'chirish`** deb yozing.")
        
    elif call.data == "adm_reports":
        cursor.execute("SELECT * FROM reports LIMIT 15")
        reps = cursor.fetchall()
        if not reps:
            bot.send_message(ADMIN_ID, "Hozircha hech qanday shikoyat yo'q. ✅")
        else:
            msg = "🚨 **Kelib tushgan shikoyatlar:**\n\n"
            for r in reps:
                msg += f"📌 ID: {r[0]} | Kimdan: `{r[1]}` ➡️ Kimga: `{r[2]}`\n"
            bot.send_message(ADMIN_ID, msg, parse_mode="Markdown")
            
    elif call.data == "adm_users":
        cursor.execute("SELECT user_id, name, age FROM users LIMIT 30")
        usrs = cursor.fetchall()
        msg = "👥 **A'zolar ro'yxati:**\n\n"
        
        markup = types.InlineKeyboardMarkup()
        for u in usrs:
            msg += f"👤 Ismi: {u[1]} | Yoshi: {u[2]} | ID: `{u[0]}`\n"
            # Har bir foydalanuvchiga admin panelidan to'g'ridan-to'g'ri bog'lanish tugmasi
            markup.add(types.InlineKeyboardButton(f"✍️ {u[1]} ga yozish", callback_data=f"adm_write_{u[0]}"))
            
        bot.send_message(ADMIN_ID, msg, parse_mode="Markdown", reply_markup=markup)
        
    elif call.data.startswith("adm_write_"):
        target_uid = call.data.split("_")[2]
        cursor.execute("UPDATE users SET status=? WHERE user_id=?", (f"adm_reply_{target_uid}", ADMIN_ID))
        conn.commit()
        bot.send_message(ADMIN_ID, f"💬 ID `{target_uid}` bo'lgan foydalanuvchiga yuboriladigan xabarni yozing:")

    conn.close()
    bot.answer_callback_query(call.id)

if __name__ == "__main__":
    t = threading.Thread(target=run_server)
    t.start()
    print("Hissiyotli AI, Anonim Chat va Admin tizimi muvaffaqiyatli yondi!")
    bot.infinity_polling()
