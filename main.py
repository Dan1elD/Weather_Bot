import telebot
import requests
import datetime
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

# Функция для создания inline-клавиатуры с кнопками "на 3 часа" и "на день"
def create_weather_inline_keyboard(city_name):
    markup = telebot.types.InlineKeyboardMarkup()
    item_hourly = telebot.types.InlineKeyboardButton("На 3 часа", callback_data=f"hourly_{city_name}")
    item_daily = telebot.types.InlineKeyboardButton("На день", callback_data=f"daily_{city_name}")
    markup.add(item_hourly, item_daily)
    return markup

# Функция для отображения клавиатуры с кнопками городов
@bot.message_handler(commands=['show_keyboard'])
def show_keyboard(message):
    markup = create_city_keyboard(message.chat.id)
    bot.send_message(message.chat.id, "Клавиатура с кнопками городов:", reply_markup=markup)

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
            
            # Создаем inline-клавиатуру для выбора времени прогноза
            markup = create_weather_inline_keyboard(city_name)
            
            bot.send_message(message.chat.id, f"Город {city_name} успешно добавлен!\n\n"
                                              f"Текущая температура: {temperature}°C\n"
                                              f"Описание погоды: {weather_description}",
                             reply_markup=markup)
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
            
            # Создаем inline-клавиатуру для выбора времени прогноза
            markup = create_weather_inline_keyboard(city_name)
            
            bot.send_message(message.chat.id, f"Текущая температура в городе {city_name}: {temperature}°C\n"
                                              f"Описание погоды: {weather_description}",
                             reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "Город не найден.")
    except Exception as e:
        bot.send_message(message.chat.id, "Произошла ошибка при получении данных о погоде.")

# Обработка inline-кнопок
@bot.callback_query_handler(func=lambda call: call.data.startswith("hourly_") or call.data.startswith("daily_"))
def handle_weather_callback(call):
    city_name = call.data.split("_")[1]
    
    if call.data.startswith("hourly_"):
        # Получите текущую погоду и отправьте сообщение с прогнозом на 3 часа
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={openweather_api_key}&units=metric"
            response = requests.get(url)
            data = response.json()
            if data["cod"] == 200:
                temperature = data["main"]["temp"]
                weather_code = data["weather"][0]["main"]
                weather_description = weather_translations.get(weather_code, "Неизвестно")
                
                # Получите прогноз на следующие 3 часа
                url_forecast = f"http://api.openweathermap.org/data/2.5/forecast?q={city_name}&appid={openweather_api_key}&units=metric"
                response_forecast = requests.get(url_forecast)
                data_forecast = response_forecast.json()
                if data_forecast["cod"] == "200":
                    hourly_forecast = data_forecast["list"][:3]  # Получите первые 3 часа
                    forecast_text = f"Прогноз погоды в городе {city_name} на 3 часа вперед:\n\n"
                    for forecast in hourly_forecast:
                        timestamp = forecast["dt"]
                        time = datetime.datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                        temperature = forecast["main"]["temp"]
                        weather_code = forecast["weather"][0]["main"]
                        weather_description = weather_translations.get(weather_code, "Неизвестно")
                        forecast_text += f"{time}: {temperature}°C, {weather_description}\n\n"
                    bot.send_message(call.message.chat.id, forecast_text)
                else:
                    bot.send_message(call.message.chat.id, "Прогноз не найден.")
            else:
                bot.send_message(call.message.chat.id, "Город не найден.")
        except Exception as e:
            bot.send_message(call.message.chat.id, "Произошла ошибка при получении прогноза погоды.")
    
    elif call.data.startswith("daily_"):
        # Получите прогноз погоды на ближайшие 24 часа и отправьте сообщение
        try:
            url_forecast = f"http://api.openweathermap.org/data/2.5/forecast?q={city_name}&appid={openweather_api_key}&units=metric"
            response_forecast = requests.get(url_forecast)
            data_forecast = response_forecast.json()
            if data_forecast["cod"] == "200":
                hourly_forecast = data_forecast["list"][:9]  # Получите прогноз на ближайшие 24 часа (каждые 3 часа)
                forecast_text = f"Прогноз погоды в городе {city_name} на ближайшие 24 часа:\n\n"
                for forecast in hourly_forecast:
                    timestamp = forecast["dt"]
                    time = datetime.datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                    temperature = forecast["main"]["temp"]
                    weather_code = forecast["weather"][0]["main"]
                    weather_description = weather_translations.get(weather_code, "Неизвестно")
                    forecast_text += f"{time}: {temperature}°C, {weather_description}\n\n"
                bot.send_message(call.message.chat.id, forecast_text)
            else:
                bot.send_message(call.message.chat.id, "Прогноз не найден.")
        except Exception as e:
            bot.send_message(call.message.chat.id, "Произошла ошибка при получении прогноза погоды.")

if __name__ == "__main__":
    print("Бот запущен.")
    bot.polling(none_stop=True)
