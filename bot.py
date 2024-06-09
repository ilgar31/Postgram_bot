import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode
from aiogram.utils import executor
import asyncio
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import PeerChannel
from config import API_TOKEN, API_ID, API_HASH
from database import *

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

client = TelegramClient('79959244367', API_ID, API_HASH)


@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    print_channels()
    print_posts()
    await message.reply("Привет! Отправьте мне название канала для мониторинга.")


@dp.message_handler()
async def add_channel_handler(message: types.Message):
    channel_username = message.text.strip()
    add_channel(channel_username)
    await message.reply(f"Канал {channel_username} добавлен для мониторинга.")
    await parse_channel(channel_username)


async def parse_channel(channel_username):
    await client.start()
    entity = await client.get_entity(channel_username)
    channel = PeerChannel(entity.id)
    history = await client(GetHistoryRequest(
        peer=channel,
        limit=10,
        offset_date=None,
        offset_id=0,
        max_id=0,
        min_id=0,
        add_offset=0,
        hash=0
    ))
    for message in history.messages:
        if message.message:
            content = message.message
            add_post(entity.id, message.id, content)
        elif message.media:
            print(message.media, message.message, message.text)
            # content = "Media content"
            # add_post(entity.id, message.id, content)
    await client.disconnect()


async def scheduled_check():
    while True:
        channels = get_channels()
        for channel in channels:
            channel_username = channel[1]
            await parse_channel(channel_username)
        await asyncio.sleep(3600)

if __name__ == '__main__':
    init_db()
    loop = asyncio.get_event_loop()
    loop.create_task(scheduled_check())
    executor.start_polling(dp, loop=loop, skip_updates=True)
