import os
import telebot
import google.generativeai as genai
from flask import Flask
from threading import Thread

# 1. НАСТРОЙКА ЛОГОВ (чтобы всё видеть в Render)
import logging
logging.basicConfig(level=logging.INFO)

# 2. ИНИЦИАЛИЗАЦИЯ КЛЮЧЕЙ
TOKEN = os.environ.get('TELEGRAM_TOKEN')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')
ADMIN_ID = os.environ.get('MY_PERSONAL_ID')

bot = telebot.TeleBot(TOKEN)
genai.configure(api_key=GEMINI_KEY)

# Настройка промпта для риелтора
SYSTEM_PROMPT = """
Ты — профессиональный ИИ-ассистент агентства недвижимости 'Prime Estate'. 
Твоя цель: вежливо ответить клиенту и квалифицировать его. 
Обязательно уточни: локацию, бюджет и когда планируют покупку.
Если клиент оставил телефон или имя — похвали его. 
Пиши кратко, профессионально и дружелюбно.
"""

# 3. ФЕЙКОВЫЙ ВЕБ-СЕРВЕР (чтобы Render не выключал бота)
app = Flask('')

@app.route('/')
def home():
    return "PrimeBot is alive!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# 4. ОБРАБОТКА СООБЩЕНИЙ
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Здравствуйте! Я PrimeBot — ваш интеллектуальный помощник. Какую недвижимость вы ищете?")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_text = message.text
    chat_id = message.chat.id

    try:
        # Работа с Gemini
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(f"{SYSTEM_PROMPT}\n\nВопрос клиента: {user_text}")
        
        bot_reply = response.text
        bot.send_message(chat_id, bot_reply)

        # Пересылка лида админу (тебе)
        if ADMIN_ID:
            lead_info = f"🔥 НОВЫЙ ЛИД!\n👤 От: @{message.from_user.username}\n💬 Текст: {user_text}"
            bot.send_message(ADMIN_ID, lead_info)

    except Exception as e:
        error_msg = str(e)
        logging.error(f"Ошибка: {error_msg}")
        # Бот честно скажет, в чем проблема (ключ, регион или фильтры)
        bot.send_message(chat_id, f"⚠️ Ошибка API: {error_msg[:100]}...")

# 5. ЗАПУСК
if __name__ == "__main__":
    # Сначала сбрасываем вебхуки, чтобы не было ошибки 409 Conflict
    bot.remove_webhook()
    
    # Запускаем Flask в отдельном потоке
    t = Thread(target=run_flask)
    t.start()
    
    print("Бот запускается...")
    # Запускаем бесконечный опрос Telegram
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
