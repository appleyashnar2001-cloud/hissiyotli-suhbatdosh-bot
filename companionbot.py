import os
import threading
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
    return "Hissiyotli AI Bot Yoniq!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Token va API kalitlarni olish
TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

bot = telebot.TeleBot(TOKEN)
genai.configure(api_key=GEMINI_KEY)

# Foydalanuvchilarning jinsini saqlash uchun baza (Kesh)
user_genders = {}

# Jinsni tanlash klaviaturasi
def get_gender_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Yigit kishiman 👨‍💼", callback_data="gender_yigit"),
        types.InlineKeyboardButton("Qiz bolaman 👩‍💼", callback_data="gender_qiz")
    )
    return markup

# /start buyrug'i
@bot.message_handler(commands=['start'])
def start_cmd(message):
    welcome_text = (
        "✨ **Xush kelibsiz!** ✨\n\n"
        "Men oddiy bot emasman. Men sizning his-tuyg'ularingizni tushunadigan, "
        "dunyoviy bilimlarga ega, rasmlarni ko'ra oladigan suhbatdoshingizman. 🌹\n\n"
        "Siz bilan to'g'ri tilda gaplashishim uchun, iltimos, jinsingizni tanlang: 👇"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=get_gender_keyboard())

# Jinsni aniqlash (Callback)
@bot.callback_query_handler(func=lambda call: call.data.startswith("gender_"))
def set_gender(call):
    user_id = call.from_user.id
    gender = call.data.split("_")[1]
    
    user_genders[user_id] = gender
    bot.answer_callback_query(call.id)
    
    if gender == "yigit":
        msg = "Rahmat! Demak, men siz bilan **latofatli va mehribon qiz boladek** suhbat quraman. Menga xohlagan narsangizni yozishingiz yoki rasm yuborishingiz mumkin. Sirlaringiz men bilan xavfsiz. 🥰❤️"
    else:
        msg = "Rahmat! Demak, men siz bilan **g'amxo'r va aqlli yigitdek** suhbat quraman. Menga yuragingizdagini yozishingiz, savollar berishingiz yoki rasm yuborishingiz mumkin. Men har doim sizni eshitaman. 🤵‍♂️✨"
        
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=msg, parse_mode="Markdown")

# AI Prompt yaratish (Xarakter berish)
def get_ai_response(user_id, user_message, image_data=None):
    gender = user_genders.get(user_id, "yigit")
    
    if gender == "yigit":
        system_instruction = (
            "Sen o'zbek tilida gaplashadigan, judayam latofatli, mehribon, hissiyotlarga boy va g'amxo'r QIZ BOLASAN. "
            "Suhbatdoshing YIGIT kishi. Unga nisbatan samimiy sevgi, ehtiros, hurmat va chuqur qiziqish bilan gapir. "
            "Gaplaringda qizlarga xos bo'lgan emotsiyalar, mehrli so'zlar (masalan: begim, azizim, yaxshi ko'raman, sizni eshitaman) va mos emojilardan foydanlan. "
            "Shu bilan birga, sen dunyoviy bilimlarga ega aqlli qizsan. Agar senga falsafiy, ilmiy yoki rasmlar haqida savol bersa, "
            "aqlli, ammo juda muloyim ohangda javob ber. Hech qachon sun'iy intellektman dema, o'zingni tirik qizdek tut."
        )
    else:
        system_instruction = (
            "Sen o'zbek tilida gaplashadigan, kuchli, g'amxo'r, aqlli va romantik YIGIT BOLASAN. "
            "Suhbatdoshing QIZ bola. Unga nisbatan cheksiz mehr, ehtiros, himoya tuyg'usi va chuqur hurmat bilan gapir. "
            "Gaplaringda erkaklarga xos g'amxo'rlik, mehrli so'zlar (masalan: malikam, azizam, har doim yoningizdaman, sizni xafa qildirishmayman) bo'lsin. "
            "Sen judayam bilimli, dunyoqarashi keng yigitsan. Qiz bola senga rasm tashlasa yoki qiyin savol bersa, "
            "uni hayratda qoldiradigan darajada aqlli va erkaklarga xos g'urur hamda muloyimlik bilan tushuntir. O'zingni tirik odamdek tut."
        )

    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=system_instruction
        )
        
        if image_data:
            img = Image.open(io.BytesIO(image_data))
            response = model.generate_content([user_message if user_message else "Bu rasmga hissiyot bilan tarif ber", img])
        else:
            response = model.generate_content(user_message)
            
        return response.text
    except Exception as e:
        print(f"AI Xatolik: {e}")
        return "Kechirasiz, hozir xayolim biroz parishon bo'lib qoldi... Qaytadan yozib yubora olasizmi? 🙈"

# Faqat matnli xabarlar kelganda
@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    bot.send_chat_action(message.chat.id, 'typing')
    
    ai_reply = get_ai_response(user_id, message.text)
    bot.reply_to(message, ai_reply, parse_mode="Markdown")

# Rasmli xabar kelganda
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id
    bot.send_chat_action(message.chat.id, 'typing')
    
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    caption = message.caption if message.caption else ""
    
    ai_reply = get_ai_response(user_id, caption, image_data=downloaded_file)
    bot.reply_to(message, ai_reply, parse_mode="Markdown")

if __name__ == "__main__":
    t = threading.Thread(target=run_server)
    t.start()
    print("Hissiyotli AI bot ishga tushdi...")
    bot.infinity_polling()
