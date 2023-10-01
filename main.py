import telegram
import requests
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
import config
import weather_translations

bot = telegram.Bot(token=config.TELEGRAM_BOT_TOKEN)
api_key = config.OPENWEATHERMAP_API_KEY

# Состояния для управления конечным автоматом
SELECTING_ACTION, ADD_CITY, ADD_CITY_CONFIRMATION = range(3)

# Клавиатура с кнопками Reply
reply_keyboard = [['Добавить в избранное ваш город']]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)

def get_weather(city):
    weather_api_url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}'
    try:
        response = requests.get(weather_api_url)
        response.raise_for_status()  # Проверка на ошибки HTTP
        data = response.json()
        if 'main' in data:
            weather_description = data['weather'][0]['description']
            if weather_description in weather_translations.weather_translations:
                weather_description = weather_translations.weather_translations[weather_description]
            temperature_kelvin = data['main']['temp']
            temperature_celsius = temperature_kelvin - 273.15
            return f'Погода в {city}: {weather_description}, Температура: {temperature_celsius:.2f}°C'
        else:
            return 'Не удалось получить данные о погоде для указанного города.'
    except requests.exceptions.RequestException as e:
        # Обработка ошибок при запросе данных о погоде
        return f'Произошла ошибка при запросе данных о погоде: {str(e)}'

# Обработка команды /start
def start(update, context):
    try:
        user_id = update.message.from_user.id
        context.bot.send_message(chat_id=user_id, text='Добро пожаловать! Я бот для отображения погоды. Введите город, чтобы узнать погоду.', reply_markup=markup)
    except Exception as e:
        # Обработка ошибок при взаимодействии с Telegram API
        print(f"Ошибка при отправке сообщения: {str(e)}")

# Обработка текстового сообщения пользователя
def handle_message(update, context):
    user_id = update.message.from_user.id
    user_message = update.message.text

    # Проверяем, является ли текст сообщения командой "Добавить в избранное ваш город"
    if user_message == 'Добавить в избранное ваш город':
        context.bot.send_message(chat_id=user_id, text='Пожалуйста, введите город, чтобы узнать погоду.', reply_markup=markup)
        return

    weather_info = get_weather(user_message)
    context.bot.send_message(chat_id=user_id, text=weather_info, reply_markup=markup)

# Функция для обновления клавиатуры с кнопками Reply
def update_reply_keyboard(context):
    user_id = context.user_data['user_id']
    user_favorite_cities = context.user_data.get('favorite_cities', [])

    # Создаем клавиатуру с кнопками Reply, включая города из избранного
    reply_keyboard = [['Добавить в избранное ваш город']]
    for city in user_favorite_cities:
        reply_keyboard.append([city])
    
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    # Обновляем клавиатуру в контексте пользователя
    context.user_data['reply_markup'] = markup

# Обработка команды "Добавить в избранное"
def add_to_favorites(update, context):
    user_id = update.message.from_user.id
    context.user_data['user_id'] = user_id  # Сохраняем ID пользователя в контексте

    # Запрашиваем у пользователя город, который он хочет добавить
    context.bot.send_message(chat_id=user_id, text='Пожалуйста, введите город, который вы хотите добавить в избранное:')
    
    return ADD_CITY  # Переходим в состояние ADD_CITY

# Обработка введенного города
def add_city(update, context):
    user_id = context.user_data['user_id']
    user_message = update.message.text

    # Проверяем, что текст команды не является городом
    if not is_valid_city(user_message):
        context.bot.send_message(chat_id=user_id, text='Пожалуйста, введите название города.', reply_markup=markup)
        return ADD_CITY

    # Получаем текущий список избранных городов пользователя (если есть)
    user_favorite_cities = context.user_data.get('favorite_cities', [])
    
    # Добавляем город в список избранных городов пользователя
    user_favorite_cities.append(user_message)
    
    # Обновляем список избранных городов в контексте пользователя
    context.user_data['favorite_cities'] = user_favorite_cities

    # Обновляем клавиатуру с кнопками Reply, включая новый город
    update_reply_keyboard(context)

    context.bot.send_message(chat_id=user_id, text=f'Город "{user_message}" добавлен в ваш список избранных городов.', reply_markup=markup)

    return ADD_CITY_CONFIRMATION  # Переходим обратно в состояние ADD_CITY_CONFIRMATION

# Проверка, является ли текст допустимым городом
def is_valid_city(city):
    if city == '/add_to_favorites':
        return False  # Исключаем команду /add_to_favorites
    # Далее можете добавить дополнительную логику проверки, является ли текст городом
    # Например, можно использовать библиотеку для геолокации или проверить список известных городов
    return True  # Вернуть True, если город допустим, и False в противном случае

# Обработка подтверждения добавления города в избранное
def add_city_confirmation(update, context):
    user_id = context.user_data['user_id']
    city = context.user_data['city_to_add']

    if city:
        user_favorite_cities = context.user_data.get('favorite_cities', [])
        user_favorite_cities.append(city)
        context.user_data['favorite_cities'] = user_favorite_cities
        update_reply_keyboard(context)
        context.bot.send_message(chat_id=user_id, text=f'Город "{city}" добавлен в ваш список избранных городов.', reply_markup=markup)
    else:
        context.bot.send_message(chat_id=user_id, text='Пожалуйста, введите название города.', reply_markup=markup)

    # Очистите контекст от города и вернитесь к обычному состоянию SELECTING_ACTION
    context.user_data.pop('city_to_add', None)
    return ConversationHandler.END

if __name__ == '__main__':
    try:
        print('Бот для отображения погоды запущен.')

        # Создание и настройка обработчиков команд и сообщений
        updater = Updater(config.TELEGRAM_BOT_TOKEN, use_context=True)
        dispatcher = updater.dispatcher

        start_handler = CommandHandler('start', start)
        dispatcher.add_handler(start_handler)

        message_handler = MessageHandler(Filters.text & ~Filters.command, handle_message)
        dispatcher.add_handler(message_handler)

        # Добавление команды "Добавить в избранное"
        add_to_favorites_handler = ConversationHandler(
            entry_points=[CommandHandler('add_to_favorites', add_to_favorites)],
            states={
                ADD_CITY: [MessageHandler(Filters.text & ~Filters.command, add_city)],
                ADD_CITY_CONFIRMATION: [MessageHandler(Filters.text & ~Filters.command, add_city_confirmation)],
            },
            fallbacks=[]
        )
        dispatcher.add_handler(add_to_favorites_handler)

        # Запуск бота
        updater.start_polling()
        updater.idle()

    except Exception as e:
        # Обработка ошибок при запуске бота и выполнении других функций
        print(f"Произошла ошибка: {str(e)}")