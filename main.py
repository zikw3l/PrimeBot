import os
import telebot
import google.generativeai as genai
from flask import Flask
from threading import Thread
import logging

# 1. НАСТРОЙКА ЛОГИРОВАНИЯ
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 2. ДАННЫЕ ИЗ RENDER (ENVIRONMENT VARIABLES)
TOKEN = os.environ.get('TELEGRAM_TOKEN')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')
ADMIN_ID = os.environ.get('MY_PERSONAL_ID')

bot = telebot.TeleBot(TOKEN)
genai.configure(api_key=GEMINI_KEY)

SYSTEM_PROMPT = """
Ты — эксперт по недвижимости в Prime Estate. 
Твоя задача: проконсультировать клиента и подтвердить, что его запрос принят.
Если клиент указал бюджет (например, 50 млн) и локацию (Сочи), подтверди, что это отличный выбор.
Если клиент оставил телефон, обязательно скажи: "Спасибо за доверие! Я передал ваш номер эксперту по Сочи, он свяжется с вами в течение 15 минут".
Пиши вежливо, уверенно и кратко.
"""

# 3. ВЕБ-СЕРВЕР ДЛЯ RENDER
app = Flask('')

@app.route('/')
def home():
    return "PrimeBot Статус: Работает"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# 4. ОБРАБОТКА КОМАНДЫ /START
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Здравствуйте! Я PrimeBot. Какую недвижимость вы ищете в Сочи или других регионах?")

# 5. ОСНОВНОЙ ОБРАБОТЧИК
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_text = message.text
    chat_id = message.chat.id

    # Сразу отправляем уведомление админу (тебе), чтобы лид не потерялся, даже если API зависнет
    if ADMIN_ID:
        try:
            lead_info = f"🔥 НОВЫЙ ЛИД!\n👤 Юзер: @{message.from_user.username or 'скрыто'}\n💬 Текст: {user_text}"
            bot.send_message(ADMIN_ID, lead_info)
        except Exception as e:
            logging.error(f"Не удалось отправить уведомление админу: {e}")

    try:
        # Настройки безопасности: отключаем блокировку "чувствительного" контента
        # (чтобы Gemini не пугалась номеров телефонов и цен)
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        # Пытаемся получить ответ от нейросети
        model = genai.GenerativeModel('gemini-1.5-flash', safety_settings=safety_settings)
        response = model.generate_content(f"{SYSTEM_PROMPT}\n\nКлиент: {user_text}")
        
        if response and response.text:
            bot.send_message(chat_id, response.text)
        else:
            # Если Gemini заблокировала ответ по другой причине
            bot.send_message(chat_id, "Ваш запрос принят! Наш менеджер уже изучает детали и скоро свяжется с вами.")

    except Exception as e:
        logging.error(f"Ошибка Gemini API: {e}")
        bot.send_message(chat_id, "Спасибо! Ваш запрос получен, мы свяжемся с вами в ближайшее время.")

# 6. ЗАПУСК
if __name__ == "__main__":
    # Очистка старых соединений
    bot.remove_webhook()
    
    # Запуск Flask
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    logging.info("Бот запущен...")
    # Запуск бота
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
