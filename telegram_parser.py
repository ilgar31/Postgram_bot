import os
import asyncio
import aiosqlite
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import PeerChannel
import shutil
from datetime import timedelta, timezone
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument

from add_record import add_data_to_server

import aiomysql

# Настройки
api_id = 22852953
api_hash = 'fdeb0befe5b3861e74113ed7862582b8'

api_id2 = 26903017
api_hash2 = 'e09d2ed4b9c117036353cfff69dc0a17'

save_path = 'telegram_data'
DB_PATH = 'channels.db'


client = TelegramClient('user', api_id, api_hash, system_version="4.16.30-vxCUSTOM")
client2 = TelegramClient('user2', api_id2, api_hash2, system_version="4.16.30-vxCUSTOM")

message_info = {}


async def fetch_messages(channel_username, last_post_date, postgram_link, postgram_account_link):
    try:
        async with client:
            channel = await client.get_entity(channel_username)

            result = await client(GetHistoryRequest(
                peer=channel,
                limit=50,
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

            message_info[channel_username] = []
            message_info_list = message_info[channel_username]
            for message in result.messages[::-1]:
                if message.date > last_post_date + timedelta(seconds=1):
                    try:
                        await save_message(channel_username, message, postgram_link, postgram_account_link, message_info_list, client)
                    except:
                        print("ошибка при сохранении сообщения")
            for message in message_info_list:
                try:
                    await add_data_to_server(message, channel_username)
                except:
                    print('ошибка, сообщение не удалось загрузить на сервер')
            try:
                shutil.rmtree(os.path.join(save_path, channel_username))
            except:
                pass


    except Exception as e:
        print(f'Не удалось получить сообщения: {e}')


async def fetch_all_messages(channel_username, postgram_link, postgram_account_link, offset_id):
    try:
        async with client2:
            channel = await client2.get_entity(channel_username)
            limit = 50

            history = await client2(GetHistoryRequest(
                peer=channel,
                offset_id=offset_id,
                offset_date=None,
                add_offset=0,
                limit=limit,
                max_id=0,
                min_id=0,
                hash=0
            ))

            if offset_id == 0:
                last_date = history.messages[0].date
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

            if not history.messages:
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute(
                        '''
                        UPDATE channels
                        SET history = ?
                        WHERE channel_username = ?
                        ''',
                        (-1, channel_username)
                    )
                    await db.commit()

            message_info[channel_username] = []
            message_info_list = message_info[channel_username]
            for message in history.messages[::-1]:
                try:
                    await save_message(channel_username, message, postgram_link, postgram_account_link, message_info_list, client2)
                except:
                    print("ошибка при сохранении сообщения")
            for message in message_info_list:
                try:
                    await add_data_to_server(message, channel_username)
                except:
                    print('ошибка, сообщение не удалось загрузить на сервер')
            try:
                shutil.rmtree(os.path.join(save_path, channel_username))
            except:
                pass

            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    '''
                    UPDATE channels
                    SET history = ?
                    WHERE channel_username = ?
                    ''',
                    (history.messages[-1].id, channel_username)
                )
                await db.commit()

    except Exception as e:
        print(f'Не удалось получить сообщения: {e}')
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                '''
                UPDATE channels
                SET history = ?
                WHERE channel_username = ?
                ''',
                (-1, channel_username)
            )
            await db.commit()


async def save_message(channel_username, message, postgram_link, postgram_account_link, message_info, client):
    channel_path = os.path.join(save_path, channel_username)
    os.makedirs(channel_path, exist_ok=True)
    media_path = ''

    async def download_media(media, destination_path):
        nonlocal media_path
        if isinstance(media, MessageMediaPhoto):
            media_path = destination_path
            await client.download_media(media, destination_path)
        elif isinstance(media, MessageMediaDocument):
            if media.document.mime_type.startswith('video/'):
                media_path = destination_path
                await client.download_media(media, destination_path)
            elif media.document.mime_type.startswith('image/'):
                media_path = destination_path
                await client.download_media(media, destination_path)

    # Download media if available
    if message.media:
        if hasattr(message.media, 'photo'):
            photo_path = os.path.join(channel_path, f"{channel_username}-{message.id}.jpeg")
            await download_media(message.media, photo_path)
        elif hasattr(message.media, 'document'):
            if message.media.document.mime_type.startswith('video/'):
                video_path = os.path.join(channel_path, f"{channel_username}-{message.id}.mp4")
                await download_media(message.media, video_path)
            elif message.media.document.mime_type.startswith('image/'):
                image_path = os.path.join(channel_path, f"{channel_username}-{message.id}.jpeg")
                await download_media(message.media, image_path)

    # Process message content
    if message.message:
        message_info.append({
            'message_id': message.id,
            'message_text': message.message,
            'message_without_url': message.message,
            'message_title_media': media_path,
            'extra_media': [],
            'channel_link': postgram_link,
            'user_link': postgram_account_link,
            'message_date': message.date + timedelta(hours=3)
        })
        if message.entities:
            offset_adjustment = 0
            for entity in message.entities:
                try:
                    if entity.document_id:
                        offset_adjustment -= entity.length - 1
                except AttributeError:
                    pass
                try:
                    start = entity.offset + offset_adjustment - 1
                    end = start + entity.length + 1
                    link_html = f'<a href="{entity.url}">{message_info[-1]["message_text"][start:end]}</a>'
                    message_info[-1]['message_text'] = (message_info[-1]['message_text'][:start] +
                                                        link_html +
                                                        message_info[-1]['message_text'][end:])
                    offset_adjustment += len(link_html) - entity.length
                except AttributeError:
                    pass
        print(message_info[-1]['message_text'])
    else:
        if message_info:
            message_info[-1]['extra_media'].append(media_path)
