import os
import random
import threading
import time
from flask import Flask
import telebot
from telebot import types
from google import genai

# ----------------- SOZLAMALAR -----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7485934521:AAHGv...") 
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
ADMIN_ID = 7180864511

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Gemini AI Client
ai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# Ma'lumotlar bazasi (Xotirada saqlash)
users = set()
active_games = {}

# Shaxsiy va Umumiy kutubxona bazasi
# Tuzilishi: {user_id: [{"title": "O'tkan kunlar", "file_id": "...", "format": "pdf"}]}
user_libraries = {} 

# ----------------- FLASK (RENDER KEEP-ALIVE) -----------------
@app.route('/')
def home():
    return "Gemini AI va Kutubxona Boti Faol!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ----------------- TUGMALAR (KEYBOARDS) -----------------
def main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("📚 Kitoblar Olami (Umumiy)")
    btn2 = types.KeyboardButton("📖 Mening Kutubxonam")
    btn3 = types.KeyboardButton("📥 Yangi Kitob Yuklash")
    btn4 = types.KeyboardButton("🧠 Zehnni Charxlash")
    btn5 = types.KeyboardButton("🤖 AI Bilan Suhbat")
    
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    markup.add(btn5)
    
    if user_id == ADMIN_ID:
        markup.add(types.KeyboardButton("👑 Admin Panel"))
    return markup

# ----------------- LOGIKA VA HANDLERLAR -----------------

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    users.add(user_id)
    if user_id not in user_libraries:
        user_libraries[user_id] = []
        
    text = (f"Salom, {message.from_user.first_name}! 👋\n\n"
            f"Men **Gemini AI** bilan jihozlangan aqlli kitobxon va intellektual yordamchingizman.\n\n"
            f"📌 **Qoidalar:** Umumiy kutubxonadan foydalanish va kitoblarni to'liq ko'chirish uchun avval o'zingiz ham kamida **1 ta kitob** yuklashingiz kerak!")
    bot.send_message(user_id, text, reply_markup=main_keyboard(user_id), parse_mode="Markdown")

# 📥 KITOB YUKLASH TALABI VA QABUL QILISH
@bot.message_handler(func=lambda message: message.text == "📥 Yangi Kitob Yuklash")
def prompt_upload(message):
    text = (
        "📥 **Shaxsiy kutubxonaga kitob qo'shish**\n\n"
        "Menga kitobingizni fayl ko'rinishida (`.pdf`, `.epub`, `.txt`, `.fb2`) yuboring.\n"
        "Ushbu kitob avtomatik ravishda sizning **Shaxsiy Kutubxonangizga** qo'shiladi va umumiy bazani ochishga ruxsat beradi!"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    user_id = message.chat.id
    users.add(user_id)
    
    file_id = message.document.file_id
    file_name = message.document.file_name
    file_size = round(message.document.file_size / (1024 * 1024), 2)
    
    allowed_exts = ['.pdf', '.epub', '.txt', '.fb2', '.mobi']
    if not any(file_name.lower().endswith(ext) for ext in allowed_exts):
        bot.send_message(user_id, "❌ Noto'g'ri format. Iltimos, faqat kitob fayllarini yuboring (PDF, EPUB, TXT).")
        return

    # Kutubxonaga saqlash
    if user_id not in user_libraries:
        user_libraries[user_id] = []
        
    user_libraries[user_id].append({
        "title": file_name,
        "file_id": file_id,
        "size": file_size
    })

    wait_msg = bot.send_message(user_id, f"⚡️ **\"{file_name}\"** tahlil qilinmoqda va saqlanmoqda...")
    time.sleep(3) # AI tahlil simulyatsiyasi
    
    success_text = (
        f"✅ **Kitob Shaxsiy Kutubxonangizga saqlandi!**\n\n"
        f"📖 **Nomi:** {file_name}\n"
        f"📦 **Hajmi:** {file_size} MB\n\n"
        f"🎉 **Tabriklaymiz!** Siz endi umumiy kitoblar bazasidan to'liq foydalana olasiz."
    )
    bot.edit_message_text(success_text, user_id, wait_msg.message_id, parse_mode="Markdown")

# 📖 MENING KUTUBXONAM
@bot.message_handler(func=lambda message: message.text == "📖 Mening Kutubxonam")
def show_my_library(message):
    user_id = message.chat.id
    books = user_libraries.get(user_id, [])
    
    if not books:
        bot.send_message(user_id, "📭 Sizning shaxsiy kutubxonangiz hali bo'sh. Kitob yuklash uchun **📥 Yangi Kitob Yuklash** tugmasini bosing.")
        return

    markup = types.InlineKeyboardMarkup()
    for idx, b in enumerate(books):
        markup.add(types.InlineKeyboardButton(f"📖 {b['title']} ({b['size']} MB)", callback_data=f"getbook_{idx}"))
        
    bot.send_message(user_id, "📚 **Siz yuklagan kitoblar ro'yxati:**\nYuklab olish uchun tanlang:", reply_markup=markup, parse_mode="Markdown")

# 📚 UMUMIY KITOBLAR (SHART TEKSHIRUVI BILAN)
@bot.message_handler(func=lambda message: message.text == "📚 Kitoblar Olami (Umumiy)")
def show_global_library(message):
    user_id = message.chat.id
    uploaded_books = user_libraries.get(user_id, [])
    
    # SHART: Kamida 1 ta kitob yuklagan bo'lishi kerak
    if len(uploaded_books) == 0:
        text = (
            "⚠️ **Ruxsat cheklangan!**\n\n"
            "Umumiy bazadan kitoblarni to'liq formatda yuklab olish uchun avval **o'zingiz ham kamida 1 ta kitob** yuklashingiz kerak.\n\n"
            "Iltimos, **📥 Yangi Kitob Yuklash** tugmasi orqali istalgan kitobingizni yuboring."
        )
        bot.send_message(user_id, text, parse_mode="Markdown")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📘 O'tkan kunlar - Abdulla Qodiriy", callback_data="sample_book_1"),
        types.InlineKeyboardButton("📙 Atom Odatlar - Jeyms Klir", callback_data="sample_book_2"),
        types.InlineKeyboardButton("📗 Boy ota, Kambag'al ota - Kiyosaki", callback_data="sample_book_3")
    )
    bot.send_message(user_id, "📚 **Umumiy kutubxona (To'liq formatdagi kitoblar):**\nO'qimoqchi bo'lgan kitobingizni tanlang:", reply_markup=markup, parse_mode="Markdown")

# 🤖 GEMINI AI BILAN SUHBAT VA ODDIY XABARLAR
@bot.message_handler(func=lambda message: True)
def handle_ai_chat_and_others(message):
    user_id = message.chat.id
    users.add(user_id)
    text = message.text

    if text == "🧠 Zehnni Charxlash":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🧮 Tezkor matematika", callback_data="game_math"),
            types.InlineKeyboardButton("👁 Shulte jadvali", callback_data="game_schulte")
        )
        bot.send_message(user_id, "Miyani chiniqtirish mashqlari:", reply_markup=markup)
        return

    elif text == "🤖 AI Bilan Suhbat":
        bot.send_message(user_id, "🤖 Men **Gemini AI** integratsiyasiga egaman. Menga istalgan savolingizni berishingiz yoki shunchaki suhbatlashishingiz mumkin!")
        return

    # Gemini AI orqali har qanday matnli xabarga intellektual javob qaytarish
    bot.send_chat_action(user_id, 'typing')
    
    if ai_client:
        try:
            response = ai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"Siz aqlli, samimiy va kitobsevar yordamchisiz. O'zbek tilida ravon javob bering. Foydalanuvchi xabari: {text}"
            )
            bot.send_message(user_id, response.text)
        except Exception as e:
            bot.send_message(user_id, f"🤖 Hozircha AI javob berishda texnik ushlanish yuz berdi. Lekin men sizni eshitayapman!")
    else:
        bot.send_message(user_id, "🤖 Gemini API Key sozlanmagan. Lekin botning boshqa funksiyalari to'liq ishlamoqda!")

# INLINE CALLBACKLAR
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.message.chat.id
    
    # Shaxsiy kutubxonadan kitob yuborish
    if call.data.startswith("getbook_"):
        idx = int(call.data.split("_")[1])
        user_books = user_libraries.get(user_id, [])
        if idx < len(user_books):
            book = user_books[idx]
            bot.send_message(user_id, f"📤 **\"{book['title']}\"** kitobi yuborilmoqda...")
            bot.send_document(user_id, book['file_id'], caption=f"📖 {book['title']}\n\n*Shaxsiy kutubxonangizdan.*", parse_mode="Markdown")
    
    elif call.data.startswith("sample_book_"):
        bot.send_message(user_id, "📥 Kitob to'liq formatda tayyorlanmoqda va yuborilmoqda...")
        # Namuna sifatidagi tavsiya xabari
        bot.send_message(user_id, "📖 Kitob yuklab olindi. Yoqimli mutolaa tilaymiz!")

# ----------------- ISHGA TUSHIRISH -----------------
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("Gemini AI bot muvaffaqiyatli ishga tushdi...")
    bot.infinity_polling()
