import asyncio
from telethon import TelegramClient, events
import logging
from telethon.tl.functions.channels import JoinChannelRequest

api_id = 22852953
api_hash = 'fdeb0befe5b3861e74113ed7862582b8'
session = 'gazp'

telethon_client = TelegramClient(session, api_id, api_hash, system_version="4.16.30-vxCUSTOM")


async def join_channel(channel_username):
    try:
        await telethon_client.connect()
        # Запрашиваем присоединение к каналу по его username
        result = await telethon_client(JoinChannelRequest(channel_username))
        print(f"Успешно подписались на канал @{channel_username}")
    except:
        print(f"Ошибка при подписке на канал @{channel_username}: error")


async def telegram_parser(username, send_message_func=None):
    '''Телеграм парсер'''

    await join_channel(username)

    channel_source = 'https://t.me/' + username
    @telethon_client.on(events.NewMessage(chats=channel_source))
    async def handler(event):
        '''Забирает посты из телеграмм каналов и посылает их в наш канал'''
        if send_message_func is None:
            print(f"Сообщение из @{username}: {event.raw_text}")
        else:
            await send_message_func(f'@{username}\n{event.raw_text}')


async def main():
    await telethon_client.start()

    channels = ['xx1000minus7xx', 'hdfugvi', 'lsdlsdt']
    for channel in channels:
        await telegram_parser(channel)

    # Клиент будет работать, пока не будет отключен
    await telethon_client.run_until_disconnected()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())