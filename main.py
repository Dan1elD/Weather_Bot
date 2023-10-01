import telebot
import requests
from config import openweather_api_key, telegram_bot_token
from weather_translations import weather_translations

bot = telebot.TeleBot(telegram_bot_token)

# Словарь для хранения добавленных городов и их описания погоды
user_cities = {}

# Функция для создания клавиатуры с кнопками городов
def create_city_keyboard(chat_id):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    if chat_id in user_cities:
        for city, weather_desc in user_cities[chat_id].items():
            item = telebot.types.KeyboardButton(city)
            markup.add(item)
    item = telebot.types.KeyboardButton('/add_city')
    markup.add(item)
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    markup = create_city_keyboard(message.chat.id)
    bot.send_message(message.chat.id, "Добро пожаловать в бота для показа погоды!", reply_markup=markup)

@bot.message_handler(commands=['add_city'])
def add_city(message):
    markup = telebot.types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "Введите название города:", reply_markup=markup)
    bot.register_next_step_handler(message, process_new_city)

def process_new_city(message):
    city_name = message.text
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={openweather_api_key}&units=metric"
        response = requests.get(url)
        data = response.json()
        if data["cod"] == 200:
            temperature = data["main"]["temp"]
            weather_description = data["weather"][0]["description"]
            
            # Проверяем, существует ли уже список городов для данного пользователя
            if message.chat.id in user_cities:
                user_cities[message.chat.id][city_name] = weather_description
            else:
                user_cities[message.chat.id] = {city_name: weather_description}
            
            bot.send_message(message.chat.id, f"Город {city_name} успешно добавлен!\n\n"
                                              f"Текущая температура: {temperature}°C\n"
                                              f"Описание погоды: {weather_description}")
            
            markup = create_city_keyboard(message.chat.id)
            bot.send_message(message.chat.id, "Добавить еще город?", reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "Город не найден.")
    except Exception as e:
        bot.send_message(message.chat.id, "Произошла ошибка при получении данных о погоде.")

@bot.message_handler(func=lambda message: message.text in user_cities.get(message.chat.id, {}))
def get_weather(message):
    city_name = message.text
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={openweather_api_key}&units=metric"
        response = requests.get(url)
        data = response.json()
        if data["cod"] == 200:
            temperature = data["main"]["temp"]
            weather_code = data["weather"][0]["main"]
            weather_description = weather_translations.get(weather_code, "Неизвестно")  # Используем переводы
            bot.send_message(message.chat.id, f"Текущая температура в городе {city_name}: {temperature}°C\n"
                                              f"Описание погоды: {weather_description}")
        else:
            bot.send_message(message.chat.id, "Город не найден.")
    except Exception as e:
        bot.send_message(message.chat.id, "Произошла ошибка при получении данных о погоде.")

if __name__ == "__main__":
    print("Бот запущен.")
    bot.polling(none_stop=True)