import os
import telebot
from telebot import types
import google.generativeai as genai
from flask import Flask
from threading import Thread
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# --- ЗАГРУЗКА КЛЮЧЕЙ ---
TOKEN = os.environ.get('TELEGRAM_TOKEN', '').strip()
GEMINI_KEY = os.environ.get('GEMINI_API_KEY', '').strip()
ADMIN_ID = os.environ.get('MY_PERSONAL_ID', '').strip()

bot = telebot.TeleBot(TOKEN)
genai.configure(api_key=GEMINI_KEY)

# Инструкция для ИИ
SYSTEM_PROMPT = """
Ты — вежливый ИИ-риелтор 'Prime Estate'. 
Веди диалог с клиентом, отвечай на его вопросы по недвижимости.
Если клиент спрашивает про цены — дай примерный реалистичный ответ и предложи варианты.
Задавай уточняющие вопросы (какой район, сколько комнат). 
Не прощайся сразу! Держи клиента в диалоге.
"""

# Хранилище диалогов (память бота)
chat_histories = {}

# --- ИНТЕРФЕЙС (КНОПКИ) ---
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("🏢 Квартиры")
    btn2 = types.KeyboardButton("🏡 Дома и Участки")
    btn3 = types.KeyboardButton("📞 Связаться с брокером")
    markup.add(btn1, btn2, btn3)
    return markup

# --- ВЕБ-СЕРВЕР ---
app = Flask('')
@app.route('/')
def home(): return "PrimeBot v2.0 is Active!"
def run_flask(): app.run(host='0.0.0.0', port=8080)

# --- ОБРАБОТЧИКИ ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Очищаем память при перезапуске
    chat_histories[message.chat.id] = None 
    text = "Здравствуйте! Я PrimeBot — ваш ИИ-ассистент по недвижимости. Выберите нужный раздел или просто напишите мне ваш вопрос."
    bot.send_message(message.chat.id, text, reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    user_text = message.text

    # 1. ОТПРАВКА УВЕДОМЛЕНИЯ АДМИНУ
    if ADMIN_ID:
        try:
            bot.send_message(ADMIN_ID, f"🔔 Клиент @{message.from_user.username} пишет:\n{user_text}")
        except Exception as e:
            logging.error(f"Ошибка отправки админу (Проверь MY_PERSONAL_ID в Render): {e}")

    # 2. ОБРАБОТКА КНОПОК
    if user_text == "📞 Связаться с брокером":
        bot.send_message(chat_id, "Оставьте ваш контактный номер, и старший брокер перезвонит вам в течение 10 минут!")
        return
    elif user_text in ["🏢 Квартиры", "🏡 Дома и Участки"]:
        user_text = f"Расскажи, какие {user_text.lower()} вы можете предложить?"

    # 3. РАБОТА С НЕЙРОСЕТЬЮ (ВЕДЕНИЕ ДИАЛОГА)
    try:
        model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=SYSTEM_PROMPT)
        
        # Создаем новую сессию, если её нет
        if chat_id not in chat_histories or chat_histories[chat_id] is None:
            chat_histories[chat_id] = model.start_chat(history=[])
        
        chat = chat_histories[chat_id]
        
        # Отправляем сообщение в контекст диалога
        response = chat.send_message(user_text)
        
        # Отвечаем клиенту
        bot.send_message(chat_id, response.text, reply_markup=get_main_keyboard())

    except Exception as e:
        error_msg = str(e)
        logging.error(f"ОШИБКА GEMINI: {error_msg}")
        # Теперь бот покажет тебе точную ошибку, чтобы мы могли её устранить
        bot.send_message(chat_id, f"⚠️ Системная ошибка API:\n{error_msg[:200]}")

if __name__ == "__main__":
    bot.remove_webhook()
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    logging.info("Бот v2.0 запущен!")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
