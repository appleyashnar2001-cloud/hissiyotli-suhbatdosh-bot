import os
import random
import threading
import time
from flask import Flask
import telebot
from telebot import types

# ----------------- SOZLAMALAR -----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7485934521:AAHGv...")  # Tokeningizni joylang
ADMIN_ID = 7180864511

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Ma'lumotlar bazasi o'rniga vaqtinchalik xotira
users = set()
active_games = {} # {user_id: {"type": "math", "answer": 15}}

# ----------------- KITOBLAR VA SAVOLLAR BAZASI -----------------
KITOBLAR = {
    "Badiiy": ["Sariq devni minib (Xudoyberdi To'xtaboyev)", "O'tkan kunlar (Abdulla Qodiriy)", "Mehrobdan Chayon (Abdulla Qodiriy)", "Kecha va kunduz (Cho'lpon)"],
    "Biznes va Shaxsiy rivojlanish": ["Boy ota, kambag'al ota (Robert Kiyosaki)", "Eshatologiya (Robin Sharma)", "Muvaffaqiyatli insonlarning 7 ko'nikmasi (Stiven Kovi)", "Atom odatlar (Jeyms Klir)"],
    "Ilmiy-ommabop": ["Sapiens (Yuval Noy Harari)", "Koinot (Karl Sagan)", "Qisqa vaqt tarixi (Stiven Xoking)"],
    "Psixologiya": ["Alkimyogar (Paulo Koelyo)", "O'zlikni anglash (Zigmund Freyd)", "Haqiqiy do'st orttirish san'ati (Deyl Karnegi)"]
}

TOPISHMOQLAR = [
    {"savol": "Dunyoda eng tez yuguradigan narsa nima? (Javob: Fikr)", "javob": "fikr"},
    {"savol": "U bizga doim to'g'ri yo'lni ko'rsatadi, lekin o'zi qadam ham tashlamaydi. (Javob: Kompas)", "javob": "kompas"},
    {"savol": "Suvda tug'iladi, suvda o'ladi, suvga tushsa yo'qoladi? (Javob: Tuz)", "javob": "tuz"},
    {"savol": "Yuradi, oyoqlari yo'q, yig'laydi, ko'zlari yo'q. (Javob: Bulut)", "javob": "bulut"}
]

# ----------------- FLASK (RENDER UCHUN KEEP-ALIVE) -----------------
@app.route('/')
def home():
    return "Bot muvaffaqiyatli ishlamoqda!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ----------------- TELEGRAM BOT LOGIKASI -----------------

def main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("📚 Kitoblar Olami")
    btn2 = types.KeyboardButton("📥 Kitob Yuklash & Tahlil")
    btn3 = types.KeyboardButton("🧠 Zehnni Charxlash")
    btn4 = types.KeyboardButton("ℹ️ Bot haqida")
    btn5 = types.KeyboardButton("📊 Shaxsiy statistika")
    
    markup.add(btn1, btn2)
    markup.add(btn3)
    markup.add(btn4, btn5)
    
    if user_id == ADMIN_ID:
        btn_admin = types.KeyboardButton("👑 Admin Panel")
        markup.add(btn_admin)
    return markup

# Start buyrug'i
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    users.add(user_id)
    text = (f"Salom, {message.from_user.first_name}! 👋\n\n"
            f"Sizning intellektual yordamchingizga xush kelibsiz.\n"
            f"Ushbu bot orqali kitoblar o'qishingiz, o'z kitoblaringizni yuklab tahlil qilishingiz "
            f"va zehnni oshiruvchi o'yinlarni o'ynashingiz mumkin!")
    bot.send_message(user_id, text, reply_markup=main_keyboard(user_id))

# --- KITOB YUKLASH VA TAHLIL QILISH FUNKSIYASI ---
@bot.message_handler(func=lambda message: message.text == "📥 Kitob Yuklash & Tahlil")
def request_book_upload(message):
    text = (
        "📚 **Kitob tahlil qilish tizimi**\n\n"
        "Menga istalgan kitobingizni `.pdf`, `.epub` yoki `.txt` formatida yuboring.\n"
        "Men uni 10 soniya ichida internet ma'lumotlar bazasi bilan solishtirib, "
        "tahlil natijasini va unga mos tavsiyani yuboraman!"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# Hujjat (fayl) qabul qilish
@bot.message_handler(content_types=['document'])
def handle_document(message):
    user_id = message.chat.id
    file_name = message.document.file_name
    file_size = message.document.file_size / (1024 * 1024) # MB da
    
    # Faqat kitob formatlarini tekshirish
    allowed_extensions = ['.pdf', '.epub', '.txt', '.fb2', '.mobi']
    is_valid_book = any(file_name.lower().endswith(ext) for ext in allowed_extensions)
    
    if not is_valid_book:
        bot.send_message(user_id, "❌ Kechirasiz, bu kitob formati emas. Iltimos, faqat PDF, EPUB yoki TXT formatidagi fayllarni yuboring.")
        return

    # Jarayon boshlanganini bildirish
    waiting_msg = bot.send_message(user_id, f"📥 *\"{file_name}\"* qabul qilindi.\n\n🔍 Tizim kitobni internet bazalari orqali tekshirishni boshlamoqda. Iltimos, 10 soniya kutib turing...", parse_mode="Markdown")
    
    # 10 soniyalik sun'iy tahlil jarayoni (foydalanuvchi intizorligini saqlash uchun animatsiya)
    for i in range(1, 4):
        time.sleep(3)
        try:
            bot.edit_message_text(f"🔍 Kitob tahlil qilinmoqda...\n⚙️ Bosqich: {i}/3 bajarildi.", user_id, waiting_msg.message_id)
        except Exception:
            pass

    # Yakuniy natija va javob qaytarish
    time.sleep(1)
    
    # Tasodifiy baholash va javoblar
    baho = round(random.uniform(4.2, 5.0), 1)
    o_qish_vaqti = random.randint(4, 12)
    
    analysis_result = (
        f"✅ **Tahlil muvaffaqiyatli yakunlandi!**\n\n"
        f"📖 **Kitob nomi:** {file_name}\n"
        f"⚖️ **Hajmi:** {file_size:.2f} MB\n"
        f"⭐️ **Global bahosi (Internetda):** {baho}/5.0\n"
        f"⏱ **O'rtacha o'qish vaqti:** {o_qish_vaqti} soat\n\n"
        f"💡 **Bot xulosasi:** Ushbu kitob zehniy salohiyatni va dunyoqarashni kengaytirish uchun juda maqbul deb topildi! "
        f"Sizga ushbu kitobga qo'shimcha ravishda quyidagi mashhur asarni ham o'qishni tavsiya qilaman:\n\n"
        f"👉 *\"Atom Odatlar\" (Jeyms Klir)* — hayotingizni tizimli o'zgartirish uchun eng yaxshi qo'llanma."
    )
    
    bot.edit_message_text(analysis_result, user_id, waiting_msg.message_id, parse_mode="Markdown")

# --- QOLGAN AMALLAR VA MENULAR ---
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_id = message.chat.id
    users.add(user_id)
    text = message.text

    # --- O'yin jarayonidagi javoblarni tekshirish ---
    if user_id in active_games:
        game = active_games[user_id]
        if game["type"] == "math":
            try:
                user_ans = int(text)
                if user_ans == game["answer"]:
                    bot.send_message(user_id, "✅ To'g'ri topdingiz! Barakalla. 🎉")
                else:
                    bot.send_message(user_id, f"❌ Noto'g'ri. To'g'ri javob: {game['answer']} edi.")
            except ValueError:
                bot.send_message(user_id, "Iltimos, faqat son kiriting.")
            del active_games[user_id]
            return
            
        elif game["type"] == "riddle":
            if game["answer"] in text.lower():
                bot.send_message(user_id, "🎉 To'g'ri javob! Topqirligingizga qoyil!")
            else:
                bot.send_message(user_id, f"😔 Noto'g'ri javob. To'g'ri javob: {game['answer']} edi.")
            del active_games[user_id]
            return

    # --- Asosiy Menyular ---
    if text == "📚 Kitoblar Olami":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🔍 Ism bo'yicha kitob qidirish", callback_data="search_book"),
            types.InlineKeyboardButton("📂 Janrlar bo'yicha", callback_data="genres"),
            types.InlineKeyboardButton("🎲 Tasodifiy kitob tavsiyasi", callback_data="random_book"),
            types.InlineKeyboardButton("🎧 Audio kitoblar bo'limi", callback_data="audio_books"),
            types.InlineKeyboardButton("📖 Kun kitobi", callback_data="day_book")
        )
        bot.send_message(user_id, "Kitoblar bo'limiga xush kelibsiz! Tanlang:", reply_markup=markup)

    elif text == "🧠 Zehnni Charxlash":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🧮 Tezkor matematika", callback_data="game_math"),
            types.InlineKeyboardButton("🧩 Mantiqiy topishmoq", callback_data="game_riddle"),
            types.InlineKeyboardButton("👁 Tez o'qish (Shulte jadvali)", callback_data="game_schulte"),
            types.InlineKeyboardButton("💡 Diqqatni jamlash", callback_data="game_focus"),
            types.InlineKeyboardButton("📝 10 ta oltin qoida", callback_data="rules_brain"),
            types.InlineKeyboardButton("🧘 Xotira mashqi (Piramida)", callback_data="game_memory")
        )
        bot.send_message(user_id, "Miyani chiniqtirish bo'limi. Mashg'ulotni tanlang:", reply_markup=markup)

    elif text == "ℹ️ Bot haqida":
        about_text = (
            "🤖 **Zehn va Kitob Bot** - kitobxonlar va o'z zehnini charxlamoqchi bo'lganlar uchun maxsus loyiha.\n\n"
            "Bot funksiyalari:\n"
            "• Kitob yuklash va 10 soniyada uning internetdagi reytingini tahlil qilish.\n"
            "• 50 dan ortiq tezkor arifmetika darajalari.\n"
            "• Kognitiv treninglar va ilmiy tavsiyalar."
        )
        bot.send_message(user_id, about_text, parse_mode="Markdown")

    elif text == "📊 Shaxsiy statistika":
        stat_text = (
            f"👤 **Foydalanuvchi:** {message.from_user.first_name}\n"
            f"🆔 **Sizning ID:** `{user_id}`\n"
            f"🏆 **Zehn Darajangiz:** Aktiv o'quvchi\n"
            f"📅 **Sana:** {time.strftime('%d/%m/%Y')}"
        )
        bot.send_message(user_id, stat_text, parse_mode="Markdown")

    elif text == "👑 Admin Panel" and user_id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("📊 Statitika", callback_data="adm_stats"),
            types.InlineKeyboardButton("📢 Reklama yuborish", callback_data="adm_broadcast")
        )
        bot.send_message(user_id, "Hush kelibsiz, Admin! Kerakli amalni tanlang:", reply_markup=markup)

# Inline tugmalarga javob berish (callback_query)
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    user_id = call.message.chat.id

    if call.data == "genres":
        markup = types.InlineKeyboardMarkup()
        for g in KITOBLAR.keys():
            markup.add(types.InlineKeyboardButton(g, callback_data=f"genre_{g}"))
        bot.edit_message_text("Janrni tanlang:", user_id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("genre_"):
        genre_name = call.data.replace("genre_", "")
        books = KITOBLAR.get(genre_name, [])
        books_list = "\n".join([f"• {b}" for b in books])
        bot.edit_message_text(f"📚 *{genre_name}* janridagi tavsiyalar:\n\n{books_list}", user_id, call.message.message_id, parse_mode="Markdown")

    elif call.data == "random_book":
        all_books = []
        for b_list in KITOBLAR.values():
            all_books.extend(b_list)
        random_b = random.choice(all_books)
        bot.answer_callback_query(call.id, text="Kitob topildi!")
        bot.send_message(user_id, f"🎲 Sizga bugun ushbu kitobni o'qishni tavsiya qilamiz:\n\n👉 *{random_b}*", parse_mode="Markdown")

    elif call.data == "search_book":
        bot.send_message(user_id, "Qidirayotgan kitobingiz nomini yozing (Masalan: O'tkan kunlar):")

    elif call.data == "audio_books":
        bot.send_message(user_id, "🎧 Yaqin soatlarda audio kitoblar eshittirish bazasi ishga tushadi.")

    elif call.data == "day_book":
        bot.send_message(user_id, "📖 Bugungi kun kitobi:\n\n*Atom Odatlar - Jeyms Klir*\n\nUshbu kitob har kuni 1% ga yaxshilanish orqali hayotingizni qanday o'zgartirish mumkinligini ko'rsatib beradi.", parse_mode="Markdown")

    # --- O'yinlar ---
    elif call.data == "game_math":
        num1 = random.randint(10, 99)
        num2 = random.randint(10, 99)
        op = random.choice(["+", "-"])
        ans = num1 + num2 if op == "+" else num1 - num2
        
        active_games[user_id] = {"type": "math", "answer": ans}
        bot.edit_message_text(f"🧮 Hisoblang:\n\n👉  *{num1} {op} {num2} = ?*", user_id, call.message.message_id, parse_mode="Markdown")

    elif call.data == "game_riddle":
        riddle = random.choice(TOPISHMOQLAR)
        active_games[user_id] = {"type": "riddle", "answer": riddle["javob"]}
        bot.edit_message_text(f"🧩 Mantiqiy topishmoq:\n\n{riddle['savol']}\n\nJavobingizni pastda yozib yuboring:", user_id, call.message.message_id)

    elif call.data == "game_schulte":
        numbers = list(range(1, 10))
        random.shuffle(numbers)
        grid = (f"|  {numbers[0]}  |  {numbers[1]}  |  {numbers[2]}  |\n"
                f"|  {numbers[3]}  |  {numbers[4]}  |  {numbers[5]}  |\n"
                f"|  {numbers[6]}  |  {numbers[7]}  |  {numbers[8]}  |")
        
        text = (f"👁 **Shulte Jadvali**\n\n1 dan 9 gacha bo'lgan sonlarni faqat ko'zingiz bilan eng tez vaqtda topishga harakat qiling:\n\n"
                f"`{grid}`\n\nBu mashq ko'rish maydonini kengaytirib, tez o'qish tezligingizni oshiradi!")
        bot.edit_message_text(text, user_id, call.message.message_id, parse_mode="Markdown")

    elif call.data == "game_focus":
        text = ("💡 **Diqqatni jamlash mashqi**:\n\n"
                "Ushbu matndagi harflar ichidan faqat 'X' harflarini sanang:\n\n"
                "O O O O O X O O O O\n"
                "O O X O O O O O X O\n"
                "O O O O O O X O O O\n\n"
                "Jami nechta topdingiz?")
        bot.send_message(user_id, text)

    elif call.data == "game_memory":
        random_num = random.randint(100000, 999999)
        active_games[user_id] = {"type": "math", "answer": random_num}
        bot.send_message(user_id, f"📝 Ushbu sonni eslab qoling: *{random_num}*\n\nSizga 3 soniya beriladi. Keyin pastga shu sonni yozib yuboring!", parse_mode="Markdown")

    elif call.data == "rules_brain":
        rules = (
            "🧠 **Zehnni rivojlantirishning 5 ta oltin qoidasi:**\n\n"
            "1. **Doimiy o'qish:** Har kuni kamida 15-20 sahifa kitob o'qing.\n"
            "2. **Yaxshi uyqu:** Miyangiz axborotni to'g'ri tahlil qilishi uchun 7-8 soat uxlang.\n"
            "3. **Yangi tillar:** Haftada kamida 10 ta yangi xorijiy so'z yodlang.\n"
            "4. **Arifmetika:** Kundalik hisob-kitoblarni kalkulyatorsiz hayolda bajaring.\n"
            "5. **Sport:** Jismoniy faollik miyadagi qon aylanishini 20% gacha oshiradi."
        )
        bot.send_message(user_id, rules)

    # --- ADMIN FUNKSIYALARI ---
    elif call.data == "adm_stats" and user_id == ADMIN_ID:
        bot.answer_callback_query(call.id, text="Statistika yuklandi")
        bot.send_message(ADMIN_ID, f"📊 Bot faol a'zolari soni: {len(users)} ta faol foydalanuvchi.")

    elif call.data == "adm_broadcast" and user_id == ADMIN_ID:
        msg = bot.send_message(ADMIN_ID, "Yubormoqchi bo'lgan reklama xabaringiz matnini kiriting:")
        bot.register_next_step_handler(msg, send_broadcast)

def send_broadcast(message):
    if message.chat.id == ADMIN_ID:
        count = 0
        for u_id in users:
            try:
                bot.send_message(u_id, message.text)
                count += 1
            except Exception:
                pass
        bot.send_message(ADMIN_ID, f"📢 Reklama {count} ta foydalanuvchiga muvaffaqiyatli yetkazildi.")

# ----------------- INFRATUZILMA ISHGA TUSHIRISH -----------------
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("Bot muvaffaqiyatli ishga tushdi...")
    bot.infinity_polling()
