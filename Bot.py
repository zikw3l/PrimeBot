import os
import telebot
import google.generativeai as genai
from flask import Flask
from threading import Thread

# 1. НАСТРОЙКИ КЛЮЧЕЙ (Берем из Secrets Replit)
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
GEMINI_API_KEY = os.environ['GEMINI_API_KEY']
MY_PERSONAL_ID = os.environ['MY_PERSONAL_ID']

# 2. НАСТРОЙКА GEMINI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Инструкция для ИИ (Промпт)
SYSTEM_PROMPT = """
Ты — экспертный ИИ-ассистент агентства недвижимости 'Prime Estate'. 
Твоя задача: квалифицировать клиента.
Обязательно узнай:
1. Тип недвижимости (квартира, дом, участок).
2. Примерный бюджет.
3. Город/Район.
4. Контактный номер (когда клиент готов к связи).

Общайся профессионально, но не слишком официально. Если клиент оставил данные, 
скажи: "Спасибо! Я передал информацию старшему брокеру, он свяжется с вами в течение 15 минут".
"""

# Хранилище контекста диалогов
user_contexts = {}


# 3. ФУНКЦИЯ УВЕДОМЛЕНИЯ ТЕБЯ (АДМИНА)
def send_lead_to_admin(chat_id, user_text, bot_reply):
    try:
        text = (f"🔥 **НОВЫЙ ЛИД В Prime Estate!**\n\n"
                f"👤 ID клиента: `{chat_id}`\n"
                f"💬 Последнее сообщение: {user_text}\n\n"
                f"🤖 Ответ бота: {bot_reply}")
        bot.send_message(MY_PERSONAL_ID, text, parse_mode='Markdown')
    except Exception as e:
        print(f"Ошибка отправки админу: {e}")


# 4. ОБРАБОТКА КОМАНДЫ /START
@bot.message_handler(commands=['start'])
def start(message):
    user_contexts[message.chat.id] = []
    welcome_text = "Здравствуйте! Я PrimeBot — ваш интеллектуальный помощник в мире недвижимости. Расскажите, какой объект вы ищете?"
    bot.send_message(message.chat.id, welcome_text)


# 5. ОБРАБОТКА СООБЩЕНИЙ
@bot.message_handler(func=lambda message: True)
def chat(message):
    chat_id = message.chat.id
    user_text = message.text

    if chat_id not in user_contexts:
        user_contexts[chat_id] = []

    # Добавляем сообщение в историю
    user_contexts[chat_id].append(f"Клиент: {user_text}")

    # Ограничиваем историю последних 10 сообщений, чтобы не тратить лимиты
    context_history = "\n".join(user_contexts[chat_id][-10:])
    full_prompt = f"{SYSTEM_PROMPT}\n\nИстория диалога:\n{context_history}\nАссистент:"

    try:
        response = model.generate_content(full_prompt)
        bot_reply = response.text

        user_contexts[chat_id].append(f"Ассистент: {bot_reply}")
        bot.send_message(chat_id, bot_reply)

        # Проверка на "Горячего лида"
        triggers = ["свяжется", "15 минут", "брокер", "записал номер"]
        if any(word in bot_reply.lower() for word in triggers):
            send_lead_to_admin(chat_id, user_text, bot_reply)

    except Exception as e:
        print(f"Ошибка Gemini: {e}")
        bot.send_message(chat_id, "Прошу прощения, небольшие технические неполадки. Повторите ваш запрос через минуту.")


# 6. ВЕБ-СЕРВЕР ДЛЯ ПОДДЕРЖКИ РАБОТЫ (KEEP-ALIVE)
app = Flask('')


@app.route('/')
def home():
    return "PrimeBot is running!"


def run_web():
    app.run(host='0.0.0.0', port=8080)


def keep_alive():
    t = Thread(target=run_web)
    t.start()


# 7. ЗАПУСК
if __name__ == "__main__":
    print("Бот запущен...")
    keep_alive()  # Запускаем веб-сервер
    bot.infinity_polling()  # Запускаем бота