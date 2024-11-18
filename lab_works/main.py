import time
import requests
from telebot.async_telebot import AsyncTeleBot
from telebot import types
import json
from datetime import datetime
import os
import asyncio

with open('keys.json', 'r', encoding='utf-8') as keys:
    key = json.load(keys)
    API_TOKEN = key['API_TOKEN']
    ADMIN_ID = key['ADMIN_ID']

bot = AsyncTeleBot(API_TOKEN)

# Путь к файлу для сохранения заявок
requests_file = 'requests.json'

RATE_LIMIT = 50  # Лимит запросов
BLOCK_TIME = 60 * 15  # Время блокировки в секундах (15 минут)

# Словари для хранения счетчиков и черного списка
request_counts = {}  # {'user_id': [count, timestamp]}
blacklist = {}  # {'user_id': unblock_time}
inactive_users = {}


# Проверка лимитов и черного списка
async def check_rate_limit(user_id):
    current_time = time.time()

    # Проверка, не находится ли пользователь в черном списке
    if user_id in blacklist:
        if current_time < blacklist[user_id]:
            return False
        else:
            # Удаляем из черного списка по истечении времени
            del blacklist[user_id]

    # Проверка и обновление счетчика запросов
    if user_id in request_counts:
        count, first_request_time = request_counts[user_id]

        # Если прошло больше BLOCK_TIME, обнуляем счетчик
        if current_time - first_request_time > BLOCK_TIME:
            request_counts[user_id] = [1, current_time]
        elif count < RATE_LIMIT:
            # Увеличиваем счетчик, если лимит не превышен
            request_counts[user_id][0] += 1
        else:
            # Добавляем в черный список
            blacklist[user_id] = current_time + BLOCK_TIME
            del request_counts[user_id]
            return False
    else:
        # Начинаем счетчик для нового пользователя
        request_counts[user_id] = [1, current_time]

    return True


# Проверяем, существует ли файл с заявками
if os.path.exists(requests_file):
    with open(requests_file, 'r', encoding='utf-8') as file:
        requests = json.load(file)
else:
    requests = {}


# Функция для сохранения заявок в файл
def save_requests():
    with open(requests_file, 'w', encoding='utf-8') as file:
        json.dump(requests, file, indent=4, ensure_ascii=False)


async def notify_admin(request_number, user_id, username, message, timestamp):
    notification_text = (
        f"Поступила новая заявка:\n"
        f"Номер заявки: {request_number}\n"
        f"ID пользователя: {user_id}\n"
        f"Имя пользователя: {username}\n"
        f"Сообщение: {message}\n"
        f"Дата и время: {timestamp}"
    )
    await bot.send_message(ADMIN_ID, notification_text)


async def notify_admin_start(user_id, username, message, timestamp):
    notification_text = (
        f"Кто-то воспользовался ботом\n"
        f"ID пользователя: {user_id}\n"
        f"Имя пользователя: {username}\n"
        f"Сообщение: {message}\n"
        f"Дата и время: {timestamp}"
    )
    await bot.send_message(ADMIN_ID, notification_text)


# Функция для напоминания пользователю спустя час
async def send_reminder(user_id):
    if user_id in inactive_users:
        current_time = time.time()
        start_time = inactive_users[user_id]
        # Проверяем, прошел ли час с момента старта
        if current_time - start_time >= 3600:  # 1 час
            await bot.send_message(user_id,
                                   "Что-то пошло не так? 🤔\nЕсли у вас возникли вопросы или проблемы, мы готовы помочь!")
            del inactive_users[user_id]  # Удаляем пользователя из списка после отправки напоминания


# Команда стартового меню
@bot.message_handler(commands=['start'])
async def main(message):
    if await check_rate_limit(message.from_user.id):
        if message.from_user.id != ADMIN_ID:
            user_id = message.from_user.id
            username = message.from_user.username or "Неизвестный пользователь"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            button1 = types.KeyboardButton("Прайс-лист")
            button2 = types.KeyboardButton("Полное описание")
            button3 = types.KeyboardButton("Открыть заявку")
            button4 = types.KeyboardButton("Закрыть заявку")
            markup.add(button1, button2, button3, button4)

            welcome_msg = """Привет!👋

    Бот *SpiritLabs* предназначен для сбора заявок по написанию лабораторных и иных работ. 

    С *прайс-листом* и *полным описанием предоставляемых услуг* Вы можете ознакомиться, нажав на соответствующую кнопку.

    Для подачи заявки Вам необходимо отправить боту *текстовое* описание задачи. 

    Вы всегда можете *дополнить описание*, отправив сообщения после оставления заявки – они будут сохранены в текущей заявке.

    ❗️*Обратите внимание*❗️

    1. Обязательно укажите Ваше *имя пользователя* Telegram для связи.

    2. Бот *не* принимает файлы, их можно будет отправить после подачи заявки, когда мы с Вами свяжемся.

    3. При допущении *ошибки* Вы можете закрыть текущую заявку, нажав на соответствующую кнопку и отправить описание задачи заново."""

            await bot.send_message(message.chat.id, welcome_msg, reply_markup=markup, parse_mode='Markdown')

            # Добавляем пользователя в список для напоминаний
            asyncio.create_task(send_reminder(user_id))

            await notify_admin_start(user_id, "@" + username, message.text, timestamp)
        else:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            button1 = types.KeyboardButton("Прайс-лист")
            button2 = types.KeyboardButton("Полное описание")
            button4 = types.KeyboardButton("/view_requests")
            markup.add(button1, button2, button4)

            welcome_msg = """Работаю в поте лица, Сэр!"""

            await bot.send_message(message.chat.id, welcome_msg, reply_markup=markup)
    else:
        await bot.reply_to(message, "Вы превысили лимит запросов. Попробуйте снова позже.")


# Команда для просмотра всех заявок администратором
@bot.message_handler(commands=['view_requests'])
async def view_requests(message):
    if message.from_user.id == ADMIN_ID:
        if requests:
            requests_list = "\n".join(
                [
                    f"Заявка #{req['request_number']} от пользователя {req['user_id']} (@{req['username']}):\n {', '.join(req['messages'])}\nДата: {req['timestamp']}\nСтатус: {req['active']}"
                    for req in requests.values()]
            )
            await bot.reply_to(message, f"Все заявки:\n{requests_list}")
        else:
            await bot.reply_to(message, "Заявок нет.")
    else:
        await bot.reply_to(message, "У вас нет прав для просмотра заявок.")


@bot.message_handler(func=lambda message: message.text == "Прайс-лист")
async def prices(message):
    if await check_rate_limit(message.from_user.id):
        price_list = """
            Здравствуйте\! Я готов помочь вам с выполнением лабораторных работ по следующим направлениям:
            \n> 1\. *Программирование на Python*\n>    \- *Базовые задачи и простые скрипты* — от 500 руб\.\n>    \- *Анализ и обработка данных \(Pandas\)* — от 800 руб\.\n>    \- *Взаимодействие с веб\-API \(Requests\)* — от 1\,000 руб\.\n>    \- *Визуализация данных \(Matplotlib\, Seaborn\)* — от 800 руб\.\n>    \- *Обработка данных в Excel \(OpenPyXl\)* — от 1\,000 руб\.\n>    \- *Работа с базами данных \(SQLite3\, MySQL\-connector\)* — от 1\,200 руб\.
            \n> 2\. *SQL и базы данных*\n>    \- *Простые SQL\-запросы* — от 500 руб\.\n>    \- *Сложные запросы с JOIN и подзапросами* — от 1\,000 руб\.\n>    \- *Агрегирование данных \(GROUP BY\, HAVING\)* — от 800 руб\.\n>    \- *Манипуляция данными \(INSERT\, UPDATE\, DELETE\)* — от 600 руб\.\n>    \- *Оконные функции \(ROW\_NUMBER\, RANK\, LEAD\, LAG\)* — от 1\,500 руб\.\n>    \- *Проектирование реляционных баз данных* — от 2\,000 руб\.
            \n> 3\. *Работа в Excel*\n>    \- *Основные функции и формулы \(СУММ\, СУММЕСЛИ\, СЧЁТЕСЛИ\)* — от 300 руб\.\n>    \- *Функции поиска данных \(ВПР\, ГПР\, ПРОСМОТРХ\)* — от 500 руб\.\n>    \- *Создание сводных таблиц* — от 800 руб\.
            \n> 4\. *Комплексные работы*\n>    \- *Комплексные задания по Python\, SQL и Excel* — от 3\,000 руб\.\n>    \- *Разработка проектов под ключ* — от 5\,000 руб\.
            \n> 5\. *Написание Telegram ботов* — от 3\,000 руб\.
            Пожалуйста\, отправьте мне описание вашей задачи\, и я свяжусь с вами для дальнейшего обсуждения\.
            """
        await bot.send_message(message.chat.id, price_list, parse_mode='MarkdownV2')
    else:
        await bot.reply_to(message, "Вы превысили лимит запросов. Попробуйте снова позже.")


# Обработчик для полного описания
@bot.message_handler(func=lambda message: message.text == "Полное описание")
async def send_description(message):
    if await check_rate_limit(message.from_user.id):
        description = """
        Выполнение лабораторных работ по следующим направлениям:

        <b>1. Программирование на Python</b>
        <b>Область применения:</b> Решение задач на Python, от простых скриптов до сложной обработки данных.
        <b>Включает работу с библиотеками:</b>
            - <b>Pandas</b>: анализ и обработка данных, работа с таблицами и фильтрацией данных.
            - <b>Requests</b>: взаимодействие с веб-API и получение данных из сети.
            - <b>Matplotlib & Seaborn</b>: построение графиков, визуализация данных, создание статистических диаграмм.
            - <b>NumPy</b>: работа с массивами и матрицами, оптимизация вычислений.
            - <b>OpenPyXl</b>: работа с Excel, обработка таблиц и создание отчетов.
            - <b>SQLite3 & MySQL-Сonnector</b>: работа с базами данных, создание запросов и управление данными.

        <b>2. SQL и базы данных</b>
        <b>Область применения:</b> Решение задач по управлению и анализу данных в базах данных, включая проектирование реляционных баз данных и оптимизацию запросов.
        <b>Работаю с различными СУБД:</b>
            - <b>MySQL</b>: реляционная база данных для создания сложных запросов и управления большими объемами данных.
            - <b>PgSQL (PostgreSQL)</b>: мощная и универсальная система для продвинутого анализа данных.
            - <b>Oracle</b>: база данных корпоративного уровня для масштабных задач.
            - <b>MS SQL Server</b>: база данных, часто используемая в крупных компаниях и для бизнес-анализа.

        <b>Использую ключевые SQL-операторы и функции:</b>
            - <b>Группировка данных</b>: с помощью GROUP BY для выполнения вычислений по группам данных и HAVING для фильтрации групп после выполнения группировки.
            - <b>Агрегирующие функции</b>: такие как MIN, MAX, SUM, COUNT для анализа и обработки данных.
            - <b>JOIN</b>: объединение данных из нескольких таблиц для комплексного анализа.
            - <b>INSERT, UPDATE, DELETE</b>: добавление, изменение и удаление данных, что позволяет эффективно управлять данными в базе.
            - <b>Подзапросы и временные таблицы(CTE)</b>: использование подзапросов для создания сложных условий и временных таблиц для промежуточных данных.
            - <b>Оконные функции</b>: такие как ROW_NUMBER, RANK, LEAD, LAG для выполнения анализа с учетом соседних строк.

        <b>Проектирование баз данных:</b>
        Проектирование реляционных баз данных с учетом бизнес-требований и оптимизации. Включает создание структур данных, определение связей между таблицами и настройку ключей для поддержания целостности данных.

        <b>3. Работа в Excel</b>
        <b>Область применения:</b> Обработка данных в Excel, создание отчетов и расчетных таблиц, анализ данных с использованием популярных функций.
        <b>Включает использование функций и инструментов:</b>
            - <b>ВПР (VLOOKUP) и ГПР (HLOOKUP)</b>: функции для поиска значений в таблицах по заданным условиям.
            - <b>ПРОСМОТРХ (XLOOKUP)</b>: расширенная версия функции ВПР, поддерживающая поиск в обоих направлениях.
            - <b>СУММ (SUM) и СУММЕСЛИ (SUMIF)</b>: для расчета сумм с учетом условий.
            - <b>СЧЁТЕСЛИ (COUNTIF) и СЧЁТЕСЛИМН (COUNTIFS)</b>: для подсчета количества значений, удовлетворяющих определённым критериям.
            - <b>Сводные таблицы</b>: создание и настройка сводных таблиц для анализа данных, их группировки и агрегации.
        """

        await bot.send_message(message.chat.id, description, parse_mode='HTML')
    else:
        await bot.reply_to(message, "Вы превысили лимит запросов. Попробуйте снова позже.")


# Обработка создания и обновления заявки
@bot.message_handler(
    func=lambda message: message.text not in ["Полное описание", "Открыть заявку", "Закрыть заявку", "Прайс-лист"])
async def handle_request(message):
    if await check_rate_limit(message.from_user.id):
        if message.from_user.id != ADMIN_ID:
            user_id = message.from_user.id
            username = message.from_user.username or "Неизвестный пользователь"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Проверяем, есть ли активная заявка для пользователя
            active_request = None
            for req_id, req in requests.items():
                if req['user_id'] == user_id and req['active']:
                    active_request = req
                    break

            if active_request is None:
                # Создаем новую заявку
                request_number = str(max(map(int, requests.keys()), default=0) + 1)
                requests[request_number] = {
                    "request_number": request_number,
                    "user_id": user_id,
                    "username": username,
                    "message": message.text,
                    "timestamp": timestamp,
                    "messages": [message.text],
                    "active": True
                }
                await notify_admin(request_number, user_id, "@" + username, message.text, timestamp)
                await bot.send_message(user_id,
                                       f"""Ваша заявка принята.\nМы свяжемся с Вами в ближайшее время!\nВы можете дополнить описание задачи, отправив сообщение боту, информация будет сохранена в текущей заявке.\nНомер заявки: {request_number}""")
            else:
                # Обновляем существующую заявку
                active_request['messages'].append(message.text)
                active_request['timestamp'] = timestamp
                await bot.send_message(user_id, "Ваше сообщение добавлено к текущей заявке.")

            save_requests()  # Сохраняем заявки в файл
        else:
            await bot.reply_to(message, "Работаю в поте лица, Сэр!")
    else:
        await bot.reply_to(message, "Вы превысили лимит запросов. Попробуйте снова позже.")


@bot.message_handler(func=lambda message: message.text == "Открыть заявку")
async def open_request(message):
    if check_rate_limit(message.from_user.id):
        await bot.reply_to(message, "Для создания заявки напишите любое сообщение.")
    else:
        await bot.reply_to(message, "Вы превысили лимит запросов. Попробуйте снова позже.")


# Обработка закрытия заявки
@bot.message_handler(func=lambda message: message.text == "Закрыть заявку")
async def close_request(message):
    if await check_rate_limit(message.from_user.id):
        user_id = message.from_user.id
        for req in requests.values():
            if req['user_id'] == user_id and req['active']:
                req['active'] = False
                await bot.reply_to(message, "Ваша заявка успешно закрыта.")
                save_requests()
                break
        else:
            await bot.reply_to(message, "У вас нет активных заявок.")
    else:
        await bot.reply_to(message, "Вы превысили лимит запросов. Попробуйте снова позже.")


if __name__ == '__main__':
    asyncio.run(bot.polling())
