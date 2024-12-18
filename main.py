from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
import requests
import json

from secret import *  # TELEGRAM_TOKEN, WEATHER_API_KEY, GEODB_API_KEY, GEODB_API_URL, WEATHER_API_URL

# Загрузка и сохранение последнего города
def load_last_city():
    try:
        with open("last_city.json", "r", encoding="utf-8") as file:
            data = json.load(file)
            return data.get("last_city")
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def save_last_city(city_name):
    with open("last_city.json", "w", encoding="utf-8") as file:
        json.dump({"last_city": city_name}, file)

# Вспомогательная функция для получения информации о городе
async def fetch_city_info(city_name: str) -> str:
    try:
        # Погода
        weather_response = requests.get(
            WEATHER_API_URL,
            params={"q": city_name, "appid": WEATHER_API_KEY, "units": "metric", "lang": "ru"},
        )
        weather_data = weather_response.json()
        if weather_response.status_code != 200:
            return f"Не удалось найти информацию о городе: {city_name}."

        # Страна и население
        country_code = weather_data['sys']['country']
        geodb_response = requests.get(
            GEODB_API_URL,
            headers={"X-RapidAPI-Key": GEODB_API_KEY, "X-RapidAPI-Host": "wft-geo-db.p.rapidapi.com"},
            params={"namePrefix": city_name, "countryIds": country_code, "limit": 1}
        )
        geodb_data = geodb_response.json()
        population = (
            geodb_data["data"][0].get("population", "Информация недоступна")
            if geodb_response.status_code == 200 and geodb_data["data"] else
            "Информация недоступна"
        )

        # Ответ
        return (
            f"Город: {weather_data['name']}\n"
            f"Страна: {weather_data['sys']['country']}\n"
            f"Температура: {weather_data['main']['temp']}°C\n"
            f"Ощущается как: {weather_data['main']['feels_like']}°C\n"
            f"Описание: {weather_data['weather'][0]['description'].capitalize()}\n"
            f"Влажность: {weather_data['main']['humidity']}%\n"
            f"Скорость ветра: {weather_data['wind']['speed']} м/с\n"
            f"Население: {population}"
        )
    except Exception as e:
        return f"Ошибка при получении данных о городе: {e}"

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [
            InlineKeyboardButton("Получить информацию о городе", callback_data="/city"),
            InlineKeyboardButton("Недавний город", callback_data="/last_city"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Привет! Я бот, который предоставляет информацию о любом городе России.\n"
        "Напишите /info для вывода всех команд или выберите одну из команд ниже.",
        reply_markup=reply_markup,
    )

# Обработка кнопок
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if query.data == "/city":
        await query.edit_message_text("Введите название города:")
        context.user_data["awaiting_city_name"] = True
    elif query.data == "/last_city":
        last_city = load_last_city()
        if last_city:
            city_info = await fetch_city_info(last_city)
            await query.edit_message_text(city_info)
        else:
            await query.edit_message_text("Информация о последнем городе отсутствует.")

# Команда /city
async def city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["awaiting_city_name"] = True
    await update.message.reply_text("Введите название города:")

# Команда /last_city
async def last_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    last_city = load_last_city()
    if last_city:
        city_info = await fetch_city_info(last_city)
        await update.message.reply_text(city_info)
    else:
        await update.message.reply_text("Информация о последнем городе отсутствует.")

# Команда /info
async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "/start - Приветствие и краткая информация о боте.\n"
        "/city - Запросить информацию о городе (необходимо ввести название города).\n"
        "/last_city - Узнать информацию о последнем введенном городе.\n"
        "/info - Получить список всех команд и их описание."
    )
    await update.message.reply_text(help_text)

# Обработка ввода названия города
async def handle_city_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get("awaiting_city_name"):
        city_name = update.message.text
        context.user_data["awaiting_city_name"] = False
        save_last_city(city_name)
        city_info = await fetch_city_info(city_name)
        await update.message.reply_text(city_info)

# Основная функция для запуска бота
def main() -> None:
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("city", city))
    application.add_handler(CommandHandler("last_city", last_city))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_city_name))

    application.run_polling()

if __name__ == "__main__":
    main()
