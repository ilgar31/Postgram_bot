import os
import asyncio
import aiosqlite
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import PeerChannel
import shutil
from datetime import timedelta, timezone
from add_record import add_data_to_server

# Настройки
api_id = '26961596'
api_hash = '84b7503f1b993d8c669f3ddfbcb939a1'
save_path = 'telegram_data'
DB_PATH = 'channels.db'

client = TelegramClient('user', api_id, api_hash, system_version="4.16.30-vxCUSTOM")


async def fetch_messages(channel_username, last_post_date, postgram_link, postgram_account_link):
    async with client:
        channel = await client.get_entity(channel_username)
        result = await client(GetHistoryRequest(
            peer=channel,
            limit=30,
            offset_date=None,
            offset_id=0,
            max_id=0,
            min_id=0,
            add_offset=0,
            hash=0
        ))

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                '''
                UPDATE channels
                SET last_post_date = ?
                WHERE channel_username = ?
                ''',
                (result.messages[0].date, channel_username)
            )
            await db.commit()

        if last_post_date.tzinfo is None:
            last_post_date = last_post_date.replace(tzinfo=timezone.utc)

        message_info = []
        for message in result.messages[::-1]:
            if message.date > last_post_date + timedelta(seconds=1):
                await save_message(channel_username, message, postgram_link, postgram_account_link, message_info)
        print(message_info)
        for message in message_info:
            add_data_to_server(message)
        shutil.rmtree(os.path.join(save_path, channel_username))


async def fetch_all_messages(channel_username, postgram_link, postgram_account_link):
    try:
        async with client:
            channel = await client.get_entity(channel_username)
            all_messages = []
            offset_id = 0
            last_id = 0
            limit = 100
            while True:
                history = await client(GetHistoryRequest(
                    peer=channel,
                    offset_id=offset_id,
                    offset_date=None,
                    add_offset=0,
                    limit=limit,
                    max_id=0,
                    min_id=0,
                    hash=0
                ))

                if not history.messages:
                    break

                if offset_id == 0:
                    last_date = history.messages[0].date

                all_messages.extend(history.messages)
                offset_id = history.messages[-1].id

            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    '''
                    UPDATE channels
                    SET last_post_date = ?
                    WHERE channel_username = ?
                    ''',
                    (last_date, channel_username)
                )
                await db.commit()

            message_info = []
            for message in all_messages[::-1]:
                await save_message(channel_username, message, postgram_link, postgram_account_link, message_info)
            print(message_info)
            for message in message_info:
                add_data_to_server(message)
            shutil.rmtree(os.path.join(save_path, channel_username))

    except Exception as e:
        print(f'Не удалось получить сообщения: {e}')


async def save_message(channel_username, message, postgram_link, postgram_account_link, message_info):
    channel_path = os.path.join(save_path, channel_username)
    os.makedirs(channel_path, exist_ok=True)

    media_path = ''

    if message.media:
        if hasattr(message.media, 'photo'):
            photo_path = os.path.join(channel_path, f"{channel_username}-{message.id}.jpeg")
            media_path = photo_path
            await client.download_media(message.media, photo_path)
        elif hasattr(message.media, 'document'):
            if message.media.document.mime_type.startswith('video/'):
                video_path = os.path.join(channel_path, f"{channel_username}-{message.id}.mp4")
                media_path = video_path
                await client.download_media(message.media, video_path)
            elif message.media.document.mime_type.startswith('image/'):
                image_path = os.path.join(channel_path, f"{channel_username}-{message.id}.jpeg")
                media_path = image_path
                await client.download_media(message.media, image_path)
    if message.message:
        message_info.append({'message_id': message.id,
                             'message_text': message.message,
                             'message_title_media': media_path,
                             'extra_media': [],
                             'channel_link': postgram_link,
                             'user_link': postgram_account_link,
                             'message_date': message.date + timedelta(hours=3)})
    else:
        if message_info:
            message_info[-1]['extra_media'].append(media_path)

