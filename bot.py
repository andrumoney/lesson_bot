from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, ConversationHandler, filters
)
from openai import OpenAI

# 🧠 Вставь свой OpenAI API-ключ
import os
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Временное хранилище генераций (user_id → количество)
user_generation_count = {}
FREE_LIMIT = 1  # сколько генераций бесплатно

# 🧩 Шаги диалога
SUBJECT, GRADE, TOPIC, FORMAT = range(4)

BOT_TOKEN = "7249401276:AAF1HfAbx35p2jMbtJk514Y4n5k4_0GTtAo"

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я помогу тебе создать план урока. Напиши /plan чтобы начать.")

# /plan → выбор предмета
async def plan_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Математика", callback_data="Математика"),
         InlineKeyboardButton("Русский язык", callback_data="Русский язык")],
        [InlineKeyboardButton("Биология", callback_data="Биология"),
         InlineKeyboardButton("История", callback_data="История")]
    ]
    await update.effective_message.reply_text("Выбери предмет:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SUBJECT

# Выбор класса
async def subject_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["subject"] = query.data

    user_id = query.from_user.id
    count = user_generation_count.get(user_id, 0)

    if count >= FREE_LIMIT:
        keyboard = [[InlineKeyboardButton("💳 Купить доступ", url="https://t.me/your_pay_link_or_site")]]
        await query.edit_message_text(
            text="🔒 Вы исчерпали лимит бесплатных генераций.\n\n"
                 "Чтобы продолжить использовать бота — оплатите доступ:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(str(i), callback_data=str(i)) for i in range(1, 12)]]
    await query.edit_message_text("Выбери класс:", reply_markup=InlineKeyboardMarkup(keyboard))
    return GRADE

# Ввод темы
async def grade_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["grade"] = query.data

    await query.edit_message_text("Напиши тему урока:")
    return TOPIC

# Выбор формата урока
async def topic_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["topic"] = update.message.text

    keyboard = [
        [InlineKeyboardButton("Обычный", callback_data="обычный"),
         InlineKeyboardButton("ЕГЭ", callback_data="ЕГЭ")],
        [InlineKeyboardButton("Повторение", callback_data="повторение"),
         InlineKeyboardButton("Игровой", callback_data="игровой")]
    ]
    await update.message.reply_text("Выбери формат урока:", reply_markup=InlineKeyboardMarkup(keyboard))
    return FORMAT

# Генерация плана урока через OpenAI

async def format_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["format"] = query.data

    subject = context.user_data["subject"]
    grade = context.user_data["grade"]
    topic = context.user_data["topic"]
    lesson_format = context.user_data["format"]

    await query.edit_message_text("Составляем план урока... ⏳")

    prompt = (
        f"Составь подробный и интересный план урока для школьников.\n"
        f"- Предмет: {subject}\n"
        f"- Класс: {grade}\n"
        f"- Тема: {topic}\n"
        f"- Формат: {lesson_format}\n"
        f"Укажи цель урока, этапы, интерактивные элементы, задания, и короткий вывод.\n"
        f"Оформление — как готовый план для учителя."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.7,
        )
        plan = response.choices[0].message.content

        # Увеличиваем счётчик генераций
        user_id = query.from_user.id
        count = user_generation_count.get(user_id, 0)
        user_generation_count[user_id] = count + 1

        await query.edit_message_text(plan[:4000])

    except Exception as e:
        await query.edit_message_text(f"Ошибка при генерации: {e}")

    return ConversationHandler.END

# Команда /cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог отменен.")
    return ConversationHandler.END

# Запуск бота
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("plan", plan_start)],
    states={
        SUBJECT: [CallbackQueryHandler(subject_chosen)],
        GRADE: [CallbackQueryHandler(grade_chosen)],
        TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, topic_entered)],
        FORMAT: [CallbackQueryHandler(format_chosen)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    per_message=True,  # 👈 добавь вот это
)

app.add_handler(CommandHandler("start", start))
app.add_handler(conv_handler)

print("✅ Бот с GPT-4o запущен")
app.run_polling()
