import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
import logging

api_id = 22852953
api_hash = 'fdeb0befe5b3861e74113ed7862582b8'

# Сессия клиента telethon
session = 'gazp'

telethon_client = TelegramClient(session, api_id, api_hash, system_version="4.16.30-vxCUSTOM", loop=None)


async def enable_wal_mode():
    async with telethon_client:
        await telethon_client.connect()
        connection = await telethon_client.get_database_connection()
        async with connection.execute('PRAGMA journal_mode=WAL;'):
            pass


async def telegram_parser(username, send_message_func=None):
    '''Телеграм парсер'''

    # Параметры из my.telegram.org
    # Канал источник новостей @prime1
    channel_source = 'https://t.me/' + username

    @telethon_client.on(events.NewMessage(chats=channel_source))
    async def handler(event):
        '''Забирает посты из телеграмм каналов и посылает их в наш канал'''

        if send_message_func is None:
            print(event.raw_text, '\n')
        else:
            await send_message_func(f'@{username}\n{event.raw_text}')


async def main():
    await enable_wal_mode()
    await telethon_client.start()

    channels = ['hdfugvi', 'xx1000minus7xx']
    tasks = [telegram_parser(channel) for channel in channels]

    await asyncio.gather(*tasks)

    await telethon_client.run_until_disconnected()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())