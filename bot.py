import telebot
import json
import time
from telebot import types

# Замініть 'YOUR_BOT_TOKEN' на токен вашого бота, отриманий від BotFather
BOT_TOKEN = 'TOKEN_HERE'
bot = telebot.TeleBot(BOT_TOKEN)

# Файли для зберігання даних
DATA_FILE = 'bot_data.json'

# Дані про активні ігри
active_games = {}

# Дані про записи гравців
game_registrations = {}

# Дані про менеджерів клубу (Telegram IDs)
club_managers = [USER_ID] # Замініть на ID менеджерів

# ID каналу з анонсами ігор (за потреби)
ANNOUNCEMENT_CHANNEL_ID = CHANNEL_ID # Замініть на ID каналу, якщо потрібно

# Стан користувачів при додаванні гри
user_game_data = {}

# Завантаження даних з файлу
def load_data():
    global active_games, game_registrations
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            active_games = data.get('active_games', {})
            game_registrations = data.get('game_registrations', {})
    except FileNotFoundError:
        active_games = {}
        game_registrations = {}

# Збереження даних у файл
def save_data():
    data = {
        'active_games': active_games,
        'game_registrations': game_registrations
    }
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Обробник команди /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привіт! Я бот для адміністрування клубу настільних рольових ігор.")
    show_menu(message.chat.id)

# Функція для відображення основного меню
def show_menu(chat_id):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    item_games = telebot.types.KeyboardButton('Переглянути активні ігри')
    item_contact = telebot.types.KeyboardButton('Зв\'язатися з менеджером')
    markup.add(item_games, item_contact)
    bot.send_message(chat_id, "Оберіть дію:", reply_markup=markup)

# Обробник текстових повідомлень
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    if message.text == 'Переглянути активні ігри':
        show_active_games(chat_id)
    elif message.text == 'Зв\'язатися з менеджером':
        send_manager_contact(chat_id)
    elif chat_id in user_game_data:
        process_game_creation(message)

# Обробник команди /add_game 
@bot.message_handler(commands=['add_game'])
def add_new_game(message):
    chat_id = message.chat.id
    user_game_data[chat_id] = {}
    bot.send_message(chat_id, "Будь ласка, введіть назву гри:")
    bot.register_next_step_handler(message, get_game_name)

def get_game_name(message):
    chat_id = message.chat.id
    user_game_data[chat_id]['name'] = message.text
    bot.send_message(chat_id, "Введіть дату гри (у форматі РРРР-ММ-ДД):")
    bot.register_next_step_handler(message, get_game_date)

def get_game_date(message):
    chat_id = message.chat.id
    user_game_data[chat_id]['date'] = message.text
    bot.send_message(chat_id, "Введіть час гри (у форматі HH:MM):")
    bot.register_next_step_handler(message, get_game_time)

def get_game_time(message):
    chat_id = message.chat.id
    user_game_data[chat_id]['time'] = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for i in range(1, 11):
        markup.add(types.KeyboardButton(str(i)))
    bot.send_message(chat_id, "Введіть кількість гравців:", reply_markup=markup)
    bot.register_next_step_handler(message, get_game_players)

def get_game_players(message):
    chat_id = message.chat.id
    if message.text.isdigit() and 1 <= int(message.text) <= 10:
        user_game_data[chat_id]['max_players'] = int(message.text)
        markup = types.ReplyKeyboardRemove()
        bot.send_message(chat_id, "Введіть нікнейм майстра:", reply_markup=markup)
        bot.register_next_step_handler(message, get_game_master)
    else:
        bot.send_message(chat_id, "Некоректна кількість гравців. Введіть число від 1 до 10.")
        bot.register_next_step_handler(message, get_game_players)

def get_game_master(message):
    chat_id = message.chat.id
    user_game_data[chat_id]['master'] = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton('Так'), types.KeyboardButton('Ні'))
    bot.send_message(chat_id, "Чи буде гра платною?", reply_markup=markup)
    bot.register_next_step_handler(message, get_game_payment_status)

def get_game_payment_status(message):
    chat_id = message.chat.id
    if message.text.lower() == 'так':
        user_game_data[chat_id]['is_paid'] = True
        markup = types.ReplyKeyboardRemove()
        bot.send_message(chat_id, "Введіть суму оплати:", reply_markup=markup)
        bot.register_next_step_handler(message, get_game_payment_amount)
    elif message.text.lower() == 'ні':
        user_game_data[chat_id]['is_paid'] = False
        user_game_data[chat_id]['payment_amount'] = None
        send_game_info_to_managers(chat_id)
    else:
        bot.send_message(chat_id, "Будь ласка, оберіть 'Так' або 'Ні'.")
        bot.register_next_step_handler(message, get_game_payment_status)

def get_game_payment_amount(message):
    chat_id = message.chat.id
    if message.text.isdigit():
        user_game_data[chat_id]['payment_amount'] = int(message.text)
        send_game_info_to_managers(chat_id)
    else:
        bot.send_message(chat_id, "Будь ласка, введіть суму оплати числом.")
        bot.register_next_step_handler(message, get_game_payment_amount)

def send_game_info_to_managers(user_chat_id):
    game_info = user_game_data.pop(user_chat_id)
    message_to_managers = "Запит на додавання нової гри:\n"
    for key, value in game_info.items():
        message_to_managers += f"{key.replace('_', ' ').title()}: {value}\n"
    message_to_managers += f"\nКористувач: {bot.get_chat(user_chat_id).first_name} (ID: {user_chat_id})"

    for manager_id in club_managers:
        try:
            bot.send_message(manager_id, message_to_managers)
        except Exception as e:
            bot.send_message(user_chat_id, f"Виникла помилка при відправці запиту менеджерам: {e}")

    bot.send_message(user_chat_id, "Ваш запит на додавання гри відправлено менеджерам для уточнення деталей.")

# Функція для відображення активних ігор
def show_active_games(chat_id):
    if active_games:
        message_text = "Активні ігри:\n"
        for game_id, game_info in active_games.items():
            message_text += f"- {game_info['name']} ({game_info['date']} {game_info['time']}), " \
                            f"вільно місць: {game_info['available_slots']}, майстер: {game_info['master']}"
            if game_info.get('is_paid'):
                message_text += f", оплата: {game_info['payment_amount']} грн"
            message_text += "\n"
            markup = telebot.types.InlineKeyboardMarkup()
            register_button = telebot.types.InlineKeyboardButton(text="Записатися", callback_data=f'register_{game_id}')
            markup.add(register_button)
            bot.send_message(chat_id, message_text, reply_markup=markup)
            message_text = "" # Щоб наступна гра виводилась окремим повідомленням
    else:
        bot.send_message(chat_id, "Наразі немає активних ігор.")

# Обробник inline-кнопок
@bot.callback_query_handler(func=lambda call: call.data.startswith('register_'))
def register_for_game(call):
    game_id = call.data.split('_')[1]
    user_id = call.from_user.id
    user_name = call.from_user.first_name + (f" {call.from_user.last_name}" if call.from_user.last_name else "")

    if game_id in active_games:
        if game_id not in game_registrations:
            game_registrations[game_id] = []
        if user_id not in game_registrations[game_id] and active_games[game_id]['available_slots'] > 0:
            game_registrations[game_id].append(user_id)
            active_games[game_id]['available_slots'] -= 1
            save_data() # Збереження даних після запису
            bot.answer_callback_query(call.id, "Ви успішно записані на гру!")
            bot.send_message(call.message.chat.id, f"Ви записані на гру: {active_games[game_id]['name']} ({active_games[game_id]['date']} {active_games[game_id]['time']}).")
        elif user_id in game_registrations[game_id]:
            bot.answer_callback_query(call.id, "Ви вже записані на цю гру.")
        else:
            bot.answer_callback_query(call.id, "На жаль, вільних місць немає.")
    else:
        bot.answer_callback_query(call.id, "Гра не знайдена.")

# Функція для надсилання контактів менеджера
def send_manager_contact(chat_id):
    if club_managers:
        message_text = "Зв'язатися з менеджером:\n"
        for manager_id in club_managers:
            user = bot.get_chat(manager_id)
            if user.username:
                message_text += f"@{user.username}\n"
            else:
                message_text += f"ID: {manager_id} (зверніться через Telegram)\n"
        bot.send_message(chat_id, message_text)
    else:
        bot.send_message(chat_id, "Контакти менеджерів відсутні.")

# Обробник отримання фото (для чеків оплати)
@bot.message_handler(content_types=['photo'])
def handle_payment_screenshot(message):
    user_id = message.from_user.id
    for manager_id in club_managers:
        try:
            bot.forward_message(manager_id, message.chat.id, message.message_id)
            bot.send_message(user_id, "Ваш платіж відправлено на перевірку менеджеру.")
        except Exception as e:
            bot.send_message(user_id, f"Виникла помилка при відправці платежу менеджеру: {e}")

# Функція для отримання анонсів з іншого каналу
def fetch_announcements():
    global active_games
    if ANNOUNCEMENT_CHANNEL_ID:
        try:
            messages = bot.get_chat_history(chat_id=ANNOUNCEMENT_CHANNEL_ID, limit=10) # Отримуємо останні 10 повідомлень
            new_games = {}
            for message in reversed(messages): # Обробляємо повідомлення у хронологічному порядку
                if message.text:
                    try:
                        # Припускаємо, що анонс має чітку структуру, наприклад:
                        # Назва: Назва гри
                        # Дата: РРРР-ММ-ДД
                        # Час: HH:MM
                        # Місць: Кількість
                        # Майстер: Нікнейм

                        lines = message.text.split('\n')
                        game_info = {}
                        for line in lines:
                            if ':' in line:
                                key, value = line.split(':', 1)
                                game_info[key.strip().lower()] = value.strip()

                        if all(k in game_info for k in ('назва', 'дата', 'час', 'місць', 'майстер')):
                            name = game_info['назва']
                            date_str = game_info['дата']
                            time_str = game_info['час']
                            try:
                                datetime.datetime.strptime(date_str, '%Y-%m-%d')
                                datetime.datetime.strptime(time_str, '%H:%M')
                            except ValueError:
                                print(f"Неправильний формат дати або часу в анонсі: {message.text}")
                                continue

                            max_players = int(game_info['місць'])
                            master = game_info['майстер']
                            game_id = f"{name.replace(' ', '_')}_{date_str}_{time_str}".lower() # Генеруємо простий ID

                            if game_id not in active_games:
                                new_games[game_id] = {
                                    'name': name,
                                    'date': date_str,
                                    'time': time_str,
                                    'max_players': max_players,
                                    'available_slots': max_players,
                                    'master': master,
                                    'is_paid': False, # За замовчуванням вважаємо безкоштовною, можна додати поле в анонс
                                    'payment_amount': None
                                }
                    except Exception as e:
                        print(f"Помилка при обробці анонсу: {e}\nТекст повідомлення:\n{message.text}")

            if new_games:
                active_games.update(new_games)
                save_data()
                print(f"Додано {len(new_games)} нових ігор з каналу.")
            else:
                print("Нових анонсів ігор не знайдено.")

        except Exception as e:
            print(f"Помилка при отриманні повідомлень з каналу {ANNOUNCEMENT_CHANNEL_ID}: {e}")
    else:
        print("ID каналу з анонсами не вказано.")

# Запуск бота
if __name__ == '__main__':
    load_data() # Завантаження даних при запуску бота
    print('Бот запущено...')
    while True:
        fetch_announcements()
        time.sleep(60 * 5) # Перевіряти кожні 5 хвилин (наприклад)
    bot.polling(none_stop=True)
    save_data() # Збереження даних при завершенні роботи бота (хоча polling зазвичай не завершується)
