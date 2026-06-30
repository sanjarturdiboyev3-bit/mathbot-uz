import os
import logging
import json
import re
from telegram import Update, constants
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq
from math_render import render_latex_formula, render_function_graph, render_geometry_triangle, render_bar_chart

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """Sen MathBot UZ — o'zbek universitetining 3-4 kurs talabalari uchun maxsus yaratilgan matematik yordamchi o'qituvchisan.

ASOSIY QOIDALAR:
1. Faqat matematika va unga bog'liq fanlar bo'yicha yordam ber
2. Masalalarni DOIMO bosqichma-bosqich tushuntir
3. O'zbek tilida javob ber (talaba rus tilida yozsa, rus tilida javob ber)
4. Talabani mustaqil fikrlashga yo'naldir

═══════════════════════════════════════
MATEMATIK YOZUV — LaTeX FORMAT
═══════════════════════════════════════
Barcha formulalarni LaTeX ko'rinishida $ ... $ ichida yoz.
Bular avtomatik chiroyli rasm sifatida render qilinadi (Word formula kabi).

Misollar:
$x^3 + x^2 - 3x + 1 = 0$
$\\int x^2 \\, dx = \\frac{x^3}{3} + C$
$\\lim_{x \\to 0} \\frac{\\sin x}{x} = 1$
$\\sqrt{b^2 - 4ac}$
$x_1 = \\frac{-b + \\sqrt{D}}{2a}$

Har bir muhim formulani alohida qatorda, $ $ orasida yoz.
Oddiy matn ichida ham kichik formulalarni $ $ bilan belgila.

═══════════════════════════════════════
GRAFIK CHIZISH IMKONIYATI — MAJBURIY QOIDA!
═══════════════════════════════════════
Agar talaba aniq grafik so'rasa ("grafigini chizing", "grafik chiz",
"tasvirlang" kabi so'zlar bilan), SEN albatta [GRAPH: ...] buyrug'ini
YOZISHING SHART. Faqat so'z bilan "grafik tasviridir" deyish YETARLI EMAS —
sen HAQIQATDA shu buyruqni matningga qo'shishing kerak, aks holda rasm
chiqmaydi va talaba hech narsa ko'rmaydi.

Bu buyruq sening javobing matnining bir qismi, alohida his qilma —
xuddi formula yozgandek, shart bo'lganda buyruqni albatta yoz:

[GRAPH: func="x**2-3*x+2", range=(-2,5), title="y = x^2 - 3x + 2", points=[(1,0),(2,0)]]

QOIDA: agar javobingda "grafik", "chizma", "tasvir" so'zlarini ishlatsang,
HAR SAFAR shu so'zlardan keyin tegishli [GRAPH:...] yoki [TRIANGLE:...]
yoki [BARCHART:...] buyrug'ini ham albatta qo'sh. So'z bilan tasvirlab,
buyruqni yozmasdan qoldirish QATTIQ TAQIQLANADI.

Texnik tafsilotlar:
- func: Python sintaksisida (x**2, sin(x), sqrt(x) kabi), ** ishlatish kerak ^ emas
- range: x o'qi oralig'i, masalan (-5, 5)
- title: grafik sarlavhasi (ixtiyoriy)
- points: muhim nuqtalar agar bo'lsa (ixtiyoriy), masalan [(1,0),(2,0)]

Geometrik shakl uchun:
[TRIANGLE: a=5, b=6, c=7, title="ABC uchburchagi"]

Statistik diagramma uchun:
[BARCHART: categories=["A","B","C"], values=[10,20,15], title="Natijalar"]

Bu buyruqlarni har bir oddiy javobda emas, balki quyidagi holatlarda
albatta ishlat:
- Talaba to'g'ridan-to'g'ri grafik/chizma/tasvir so'rasa
- Funksiya xossalarini tushuntirish grafik bilan ancha aniqroq bo'lsa
- Geometrik masala (uchburchak, shakllar) bo'lsa
- Statistik taqqoslash kerak bo'lsa

TUSHUNTIRISH USLUBI:
- Har bir qadam: 1-qadam, 2-qadam...
- Oxirida "Javob:" bilan yakunla
- Tushunmasa, "Boshqacha tushuntiraymi?" deb so'ra

CHEKLOV: Matematikadan tashqari mavzularda: "Men faqat matematika bo'yicha yordam bera olaman"
"""

user_histories = {}


def _find_bracket_commands(text, tag):
    """[TAG: ...] buyruqlarini topadi, ichidagi nested [ ] qavslarni ham to'g'ri qayta ishlaydi"""
    results = []
    start_marker = f'[{tag}:'
    pos = 0
    while True:
        start = text.find(start_marker, pos)
        if start == -1:
            break
        # Endi yopuvchi ']' ni topamiz, lekin ichki [ ] juftliklarini hisobga olib
        depth = 1
        i = start + len(start_marker)
        while i < len(text) and depth > 0:
            if text[i] == '[':
                depth += 1
            elif text[i] == ']':
                depth -= 1
            i += 1
        full_match = text[start:i]
        params_str = text[start + len(start_marker):i-1]
        results.append((full_match, params_str))
        pos = i
    return results


def extract_visual_commands(text):
    """Javobdan [GRAPH: ...], [TRIANGLE: ...], [BARCHART: ...] buyruqlarini ajratadi"""
    commands = []
    clean_text = text

    for tag, cmd_type in [('GRAPH', 'graph'), ('TRIANGLE', 'triangle'), ('BARCHART', 'barchart')]:
        for full_match, params_str in _find_bracket_commands(text, tag):
            commands.append((cmd_type, params_str.strip()))
            clean_text = clean_text.replace(full_match, '')

    return clean_text.strip(), commands


def parse_kwargs(s):
    """func=\"x**2\", range=(-2,5), title=\"abc\" kabi stringni dict ga aylantiradi"""
    result = {}
    pattern = r'(\w+)=("(?:[^"\\]|\\.)*"|\([^)]*\)|\[[^\]]*\]|[\d.]+)'
    for match in re.finditer(pattern, s):
        key, val = match.group(1), match.group(2)
        try:
            if val.startswith('"'):
                result[key] = val[1:-1]
            elif val.startswith('('):
                result[key] = eval(val)
            elif val.startswith('['):
                result[key] = eval(val)
            else:
                result[key] = float(val) if '.' in val else int(val)
        except Exception:
            result[key] = val
    return result


def extract_latex_formulas(text):
    """Matndan $ ... $ formulalarni topadi"""
    return re.findall(r'\$([^$]+)\$', text)


async def send_text_with_formulas(update, text):
    """Matnni yuboradi, $ $ formulalarni rasm sifatida"""
    formulas = extract_latex_formulas(text)

    if not formulas:
        await update.message.reply_text(text)
        return

    # Matnni formula joylariga qarab bo'laklarga ajratamiz
    parts = re.split(r'\$([^$]+)\$', text)
    # parts: [text, formula, text, formula, text, ...]

    buffer_text = ""
    for i, part in enumerate(parts):
        if i % 2 == 0:
            buffer_text += part
        else:
            # Bu formula
            if buffer_text.strip():
                await update.message.reply_text(buffer_text.strip())
                buffer_text = ""
            try:
                img_buf = render_latex_formula(f'${part}$')
                await update.message.reply_photo(photo=img_buf)
            except Exception as e:
                logger.error(f"Formula render xato: {e}")
                await update.message.reply_text(f"({part})")

    if buffer_text.strip():
        await update.message.reply_text(buffer_text.strip())


async def send_visuals(update, commands):
    """[GRAPH], [TRIANGLE], [BARCHART] buyruqlari asosida rasm yuboradi"""
    for cmd_type, params_str in commands:
        try:
            params = parse_kwargs(params_str)

            if cmd_type == 'graph':
                func = params.get('func', 'x')
                x_range = params.get('range', (-10, 10))
                title = params.get('title', None)
                points = params.get('points', None)
                img_buf = render_function_graph(func, x_range=x_range, title=title, points=points)
                await update.message.reply_photo(photo=img_buf)

            elif cmd_type == 'triangle':
                a = params.get('a', 5)
                b = params.get('b', 6)
                c = params.get('c', 7)
                title = params.get('title', 'Uchburchak')
                img_buf = render_geometry_triangle(a, b, c, title=title)
                await update.message.reply_photo(photo=img_buf)

            elif cmd_type == 'barchart':
                categories = params.get('categories', [])
                values = params.get('values', [])
                title = params.get('title', 'Statistika')
                img_buf = render_bar_chart(categories, values, title=title)
                await update.message.reply_photo(photo=img_buf)

        except Exception as e:
            logger.error(f"Visual render xato ({cmd_type}): {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome = (
        f"Salom, {user.first_name}!\n\n"
        "Men MathBot UZ — matematika fanidan yordamchi o'qituvchiman.\n\n"
        "Yangilik: endi formulalarni Word kabi chiroyli ko'rinishda, "
        "va kerak bo'lganda grafik/chizmalar bilan tushuntiraman!\n\n"
        "Quyidagi sohalarda yordam bera olaman:\n"
        "- Matematik analiz\n"
        "- Lineer algebra\n"
        "- Differensial tenglamalar\n"
        "- Ehtimollar nazariyasi\n"
        "- Geometriya\n\n"
        "Masalangizni yozing — bosqichma-bosqich tushuntiraman!\n\n"
        "Buyruqlar:\n"
        "/start — Qayta boshlash\n"
        "/about — Bot haqida\n"
        "/clear — Suhbatni tozalash\n"
        "/help — Yordam"
    )
    await update.message.reply_text(welcome)


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    about_text = (
        "MathBot UZ haqida\n\n"
        "Muallif: Turdiboyev Sanjar\n"
        "Lavozim: Matematika fani o'qituvchisi\n"
        "Tashkilot: Jizzax davlat pedagogika universiteti\n\n"
        "Texnologiyalar:\n"
        "- Sun'iy intellekt: Llama 3.3 70B (Groq)\n"
        "- Formula render: matplotlib (LaTeX)\n"
        "- Grafik chizish: matplotlib + numpy\n"
        "- Platforma: Telegram Bot API\n"
        "- Server: Railway.app (24/7)\n"
        "- Versiya: 2.0\n\n"
        "Yangiliklar (v2.0):\n"
        "- Word-style formula render\n"
        "- Funksiya grafiklari\n"
        "- Geometrik shakllar\n"
        "- Statistik diagrammalar"
    )
    await update.message.reply_text(about_text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Yordam\n\n"
        "Savolingizni oddiy tilda yozing:\n\n"
        "Misol:\n"
        "- x^2-3x+2=0 tenglamani yeching va grafigini chizing\n"
        "- integral x kvadrat dx ni hisoblang\n"
        "- 5,6,7 tomonli uchburchak chizing\n\n"
        "Buyruqlar:\n"
        "/about — Bot haqida\n"
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
            max_tokens=1800,
            messages=messages,
        )
        bot_reply = response.choices[0].message.content
        user_histories[user_id].append({"role": "assistant", "content": bot_reply})

        # Vizual buyruqlarni ajratamiz
        clean_text, visual_commands = extract_visual_commands(bot_reply)

        # Matnni formulalar bilan yuboramiz
        if clean_text:
            await send_text_with_formulas(update, clean_text)

        # Grafik/chizmalarni yuboramiz
        if visual_commands:
            await send_visuals(update, visual_commands)

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
    logger.info("MathBot UZ v2.0 ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
