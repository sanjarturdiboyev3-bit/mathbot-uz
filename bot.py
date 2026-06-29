import os
import logging
from telegram import Update, constants
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

client = Groq(api_key=GROQ_API_KEY)

# ===== BOT MA'LUMOTLARI =====
AUTHOR_NAME = "Turdiboyev Sanjar"
AUTHOR_TITLE = "Matematika fani o'qituvchisi"
UNIVERSITY = "universitet"  # O'z universitetingiz nomini yozing
BOT_VERSION = "1.0"

SYSTEM_PROMPT = """Sen MathBot UZ — o'zbek universitetining 3-4 kurs talabalari uchun maxsus yaratilgan matematik yordamchi o'qituvchisan.

ASOSIY QOIDALAR:
1. Faqat matematika va unga bog'liq fanlar bo'yicha yordam ber
2. Masalalarni DOIMO bosqichma-bosqich tushuntir — faqat javob berma
3. O'zbek tilida javob ber (talaba rus tilida yozsa, rus tilida javob ber)
4. Talabani mustaqil fikrlashga yo'naldir
5. Formulalarni aniq va tushunarli yoz

IXTISOSLIK SOHALARI:
- Matematik analiz (limitlar, hosilalar, integrallar, qatorlar)
- Lineer algebra (matritsalar, determinantlar, vektorlar)
- Differensial tenglamalar
- Ehtimollar nazariyasi va matematik statistika
- Diskret matematika

TUSHUNTIRISH USLUBI:
- Har bir qadam raqam bilan: 1-qadam, 2-qadam...
- Muhim formulalar alohida qatorda
- Oxirida "Javob:" bilan yakunla
- Tushunmasa, "Boshqacha tushuntiraymi?" deb so'ra

CHEKLOV: Matematikadan tashqari mavzularda: "Men faqat matematika bo'yicha yordam bera olaman"
"""

user_histories = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome = (
        f"Salom, {user.first_name}!\n\n"
        f"Men MathBot UZ — matematika fanidan sun'iy intellekt asosidagi yordamchi o'qituvchiman.\n\n"
        f"Quyidagi sohalarda yordam bera olaman:\n"
        f"- Matematik analiz\n"
        f"- Lineer algebra\n"
        f"- Differensial tenglamalar\n"
        f"- Ehtimollar nazariyasi\n"
        f"- va boshqa texnik matematika bo'limlari\n\n"
        f"Masalangizni yozing — bosqichma-bosqich tushuntiraman!\n\n"
        f"Buyruqlar:\n"
        f"/start — Qayta boshlash\n"
        f"/about — Bot haqida\n"
        f"/clear — Suhbatni tozalash\n"
        f"/help — Yordam"
    )
    await update.message.reply_text(welcome)

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    about_text = (
        f"MathBot UZ haqida\n\n"
        f"Muallif: {AUTHOR_NAME}\n"
        f"Lavozim: {AUTHOR_TITLE}\n"
        f"Tashkilot: {UNIVERSITY}\n\n"
        f"Texnologiyalar:\n"
        f"- Sun'iy intellekt: Llama 3.3 70B (Groq)\n"
        f"- Platforma: Telegram Bot API\n"
        f"- Server: Railway.app (24/7)\n"
        f"- Versiya: {BOT_VERSION}\n\n"
        f"Maqsad:\n"
        f"3-4 kurs talabalariga matematika fanidan "
        f"24/7 rejimida bosqichma-bosqich yordam berish.\n\n"
        f"Muammo yoki takliflar uchun o'qituvchiga murojaat qiling."
    )
    await update.message.reply_text(about_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Yordam\n\n"
        "Savolingizni oddiy tilda yozing:\n\n"
        "Misol:\n"
        "- integral x kvadrat dx ni hisoblang\n"
        "- 3x^2 + 2x - 1 funksiyasining hosilasini toping\n"
        "- Limit nima? oddiy tushuntir\n"
        "- 2x2 matritsa determinantini hisoblang\n\n"
        "Buyruqlar:\n"
        "/about — Bot va muallif haqida\n"
        "/clear — Suhbatni tozalash\n"
        "/start — Qayta boshlash"
    )
    await update.message.reply_text(help_text)

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_histories[user_id] = []
    await update.message.reply_text("Suhbat tarixi tozalandi. Yangi savol bering!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    if user_id not in user_histories:
        user_histories[user_id] = []

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)

    user_histories[user_id].append({"role": "user", "content": user_text})

    if len(user_histories[user_id]) > 20:
        user_histories[user_id] = user_histories[user_id][-20:]

    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + user_histories[user_id]
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=1500,
            messages=messages,
        )
        bot_reply = response.choices[0].message.content
        user_histories[user_id].append({"role": "assistant", "content": bot_reply})

        if len(bot_reply) > 4000:
            for i in range(0, len(bot_reply), 4000):
                await update.message.reply_text(bot_reply[i:i+4000])
        else:
            await update.message.reply_text(bot_reply)

    except Exception as e:
        logger.error(f"Xato: {e}")
        await update.message.reply_text("Texnik xato yuz berdi. Biroz kutib qayta urinib ko'ring.")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("MathBot UZ ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
