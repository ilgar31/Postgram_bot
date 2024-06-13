import logging
import os
import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from telegram_parser import fetch_messages, fetch_all_messages, save_message
from datetime import datetime

# Настройки
API_TOKEN = '7315863013:AAGjumOSsxT3vNXi9CAJMQNWOJhKJwO2j8Q'
save_path = 'telegram_data'
DB_PATH = 'channels.db'

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())


class Form(StatesGroup):
    waiting_for_postgram_link = State()
    waiting_for_postgram_account_link = State()
    waiting_for_channel_username = State()
    waiting_for_history_choice = State()
    waiting_for_channel_selection = State()
    waiting_for_deletion_confirmation = State()


# async def init_db():
#     async with aiosqlite.connect(DB_PATH) as db:
#         await db.execute('''
#             CREATE TABLE IF NOT EXISTS channels (
#                 user_id INTEGER,
#                 channel_username TEXT,
#                 channel_url TEXT,
#                 account_url TEXT,
#                 last_post_date TEXT DEFAULT NULL
#             )
#         ''')
#         await db.commit()


@dp.message_handler(commands='start')
async def cmd_start(message: types.Message, start_bot=True):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Мои каналы"), KeyboardButton("Добавить канал"))
    if start_bot:
        await message.answer(
        "Привет! Я предназначен для автоматического парсинга данных с канала пользователя и выгрузки всех постов на сайт Postgram.ru для дальнейшего продвижения и набора аудитории.",
        reply_markup=markup
        )
    else:
        await message.answer("🔮 Главное меню", reply_markup=markup)


@dp.message_handler(lambda message: message.text == "Добавить канал")
async def handle_add_channel(message: types.Message):
    await Form.waiting_for_postgram_link.set()
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Назад"))
    await message.answer("Пожалуйста, отправьте ссылку на канал на сайте Postgram.ru.", reply_markup=markup)


@dp.message_handler(state=Form.waiting_for_postgram_link, content_types=types.ContentType.TEXT)
async def process_postgram_link(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await state.finish()
        await cmd_start(message, False)
        return
    await state.update_data(postgram_link=message.text)
    await Form.waiting_for_postgram_account_link.set()
    await message.answer("Пожалуйста, отправьте ссылку на ваш аккаунт на сайте Postgram.ru.", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("Назад")))


@dp.message_handler(state=Form.waiting_for_postgram_account_link, content_types=types.ContentType.TEXT)
async def process_postgram_account_link(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await state.finish()
        await cmd_start(message, False)
        return
    await state.update_data(postgram_account_link=message.text)
    await Form.waiting_for_channel_username.set()
    await message.answer("Пожалуйста, отправьте username вашего Telegram канала.", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("Назад")))


@dp.message_handler(state=Form.waiting_for_channel_username, content_types=types.ContentType.TEXT)
async def process_channel_username(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await state.finish()
        await cmd_start(message, False)
        return
    await state.update_data(channel_username=message.text)
    await Form.waiting_for_history_choice.set()
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Да"), KeyboardButton("Нет"), KeyboardButton("Назад"))
    await message.answer("Нужно ли спарсить историю постов (посты до добавления канала в бота)?", reply_markup=markup)


@dp.message_handler(state=Form.waiting_for_history_choice, content_types=types.ContentType.TEXT)
async def process_history_choice(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await state.finish()
        await cmd_start(message, False)
        return
    user_id = message.from_user.id
    user_data = await state.get_data()
    postgram_link = user_data['postgram_link']
    postgram_account_link = user_data['postgram_account_link']
    channel_username = user_data['channel_username']

    if message.text == "Да" or message.text == "Нет":
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute('SELECT COUNT(*) FROM channels WHERE user_id = ?', (user_id,))
            count = await cursor.fetchone()
            if count[0] >= 3:
                await message.answer("Вы не можете добавить более 3 каналов.")
            else:
                await db.execute(
                    'INSERT INTO channels (user_id, channel_username, channel_url, account_url, last_post_date) VALUES (?, ?, ?, ?, ?)',
                    (user_id, channel_username, postgram_link, postgram_account_link, datetime.now().strftime('%Y-%m-%d %H:%M:%S') if message.text == "Да" else None)
                )
                await db.commit()
                await message.answer("Канал успешно добавлен на парсинг.", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("Мои каналы"), KeyboardButton("Добавить канал")))
                if message.text == "Да":
                    try:
                        await fetch_all_messages(channel_username, postgram_link, postgram_account_link)
                    except:
                        pass

    await state.finish()


@dp.message_handler(lambda message: message.text == "Мои каналы")
async def handle_my_channels(message: types.Message):
    user_id = message.from_user.id
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT channel_username FROM channels WHERE user_id = ?', (user_id,))
        rows = await cursor.fetchall()
        for row in rows:
            markup.add(KeyboardButton(row[0]))
    markup.add(KeyboardButton("Назад"))
    await Form.waiting_for_channel_selection.set()
    await message.answer("Ваши каналы:", reply_markup=markup)


@dp.message_handler(state=Form.waiting_for_channel_selection, content_types=types.ContentType.TEXT)
async def handle_channel_info(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await state.finish()
        await cmd_start(message, False)
        return
    user_id = message.from_user.id
    channel_username = message.text

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT * FROM channels WHERE user_id = ? AND channel_username = ?', (user_id, channel_username))
        channel = await cursor.fetchone()
        if channel:
            await state.update_data(selected_channel=channel)
            markup = ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(KeyboardButton("Удалить канал"), KeyboardButton("Назад"))
            await message.answer(f"Информация о канале {channel_username}:\nСсылка канала на Postgram: {channel[2]}\nСсылка аккаунта на Postgram: {channel[3]}", reply_markup=markup)
            await Form.waiting_for_deletion_confirmation.set()


@dp.message_handler(state=Form.waiting_for_deletion_confirmation, content_types=types.ContentType.TEXT)
async def handle_remove_channel(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await state.finish()
        await cmd_start(message, False)
        return
    user_id = message.from_user.id
    user_data = await state.get_data()
    selected_channel = user_data.get('selected_channel')
    if selected_channel:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('DELETE FROM channels WHERE user_id = ? AND channel_username = ?', (user_id, selected_channel[1]))
            await db.commit()
        await message.answer("Канал успешно удален.", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("Мои каналы"), KeyboardButton("Добавить канал")))
    await state.finish()


async def check_new_messages():
    while True:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute('SELECT * FROM channels')
            channels = await cursor.fetchall()
            for channel in channels:
                try:
                    await fetch_messages(channel[1], datetime.strptime(channel[4][:-6], '%Y-%m-%d %H:%M:%S'), channel[2], channel[3])
                except:
                    pass
        await asyncio.sleep(120)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(check_new_messages())
    executor.start_polling(dp, skip_updates=True)