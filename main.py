import os
import telebot
import google.generativeai as genai
from flask import Flask
from threading import Thread
import logging

# Настройка логирования для Render
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 1. ЗАГРУЗКА ДАННЫХ
TOKEN = os.environ.get('TELEGRAM_TOKEN')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')
ADMIN_ID = os.environ.get('MY_PERSONAL_ID')

bot = telebot.TeleBot(TOKEN)
genai.configure(api_key=GEMINI_KEY)

# Инструкция для ИИ
SYSTEM_PROMPT = """
Ты — профессиональный ИИ-ассистент агентства недвижимости 'Prime Estate'. 
Твоя цель: вежливо ответить клиенту и квалифицировать его. 
Обязательно уточни: локацию, бюджет и когда планируют покупку.
Если клиент оставил телефон или имя — похвали его и скажи, что эксперт свяжется скоро.
Пиши кратко, профессионально и дружелюбно.
"""

# 2. ВЕБ-СЕРВЕР ДЛЯ RENDER (чтобы сервис не засыпал)
app = Flask('')

@app.route('/')
def home():
    return "PrimeBot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# 3. ОБРАБОТКА КОМАНДЫ /START
@bot.message_handler(commands=['start'])
def send_welcome(message):
    logging.info(f"User {message.chat.id} started the bot")
    bot.reply_to(message, "Здравствуйте! Я PrimeBot — ваш интеллектуальный помощник. Какую недвижимость вы ищете?")

# 4. ОСНОВНОЙ ОБРАБОТЧИК СООБЩЕНИЙ
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_text = message.text
    chat_id = message.chat.id

    try:
        # Пытаемся по очереди разные названия моделей, чтобы избежать ошибки 404
        response = None
        for model_name in ['gemini-1.5-flash', 'gemini-1.5-flash-latest', 'gemini-pro']:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(f"{SYSTEM_PROMPT}\n\nКлиент пишет: {user_text}")
                if response:
                    break
            except Exception as e:
                logging.warning(f"Модель {model_name} недоступна: {e}")
                continue

        if response and response.text:
            bot_reply = response.text
            bot.send_message(chat_id, bot_reply)
            
            # Отправка уведомления админу (вам)
            if ADMIN_ID:
                lead_info = f"🔥 НОВЫЙ ЛИД!\n👤 От: @{message.from_user.username or 'скрыто'}\n💬 Текст: {user_text}"
                bot.send_message(ADMIN_ID, lead_info)
        else:
            bot.send_message(chat_id, "Извините, я немного задумался. Попробуйте перефразировать запрос.")

    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")
        bot.send_message(chat_id, f"⚠️ Ошибка API: {str(e)[:50]}...")

# 5. ЗАПУСК ПРИЛОЖЕНИЯ
if __name__ == "__main__":
    # Сброс вебхуков для предотвращения ошибки 409 Conflict
    bot.remove_webhook()
    
    # Запуск Flask в фоновом потоке
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    logging.info("Бот запускается в режиме Polling...")
    # Запуск бесконечного опроса
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
