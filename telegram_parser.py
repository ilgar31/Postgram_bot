import os
import asyncio
import aiosqlite
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import PeerChannel
import shutil
from datetime import timedelta, timezone
from add_record import add_data_to_server
import mysql.connector
from mysql.connector import Error
import threading

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


async def add_tg_link(postgram_link, channel_username, host='db10.ipipe.ru', database='alexman_db1', user='alexman_db1', password='iGMqjTwJmwte'):
    try:
        connection = mysql.connector.connect(
            host=host,
            database=database,
            user=user,
            password=password
        )

        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)

            sql = "UPDATE communities SET tg_link = %s WHERE slug = %s"
            cursor.execute(sql, ('https://t.me/' + channel_username, postgram_link.split('/')[-1],))
            result = cursor.fetchone()

            connection.commit()

            if connection.is_connected():
                cursor.close()
                connection.close()
    except Error as e:
        print(e)


async def fetch_messages(channel_username, last_post_date, postgram_link, postgram_account_link):
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
                await save_message(channel_username, message, postgram_link, postgram_account_link, message_info_list, client)
        try:
            tasks = [asyncio.create_task(add_data_to_server(message, channel_username)) for message in
                     message_info_list]
            await asyncio.gather(*tasks)
        except:
            print('ошибка, сообщение не удалось загрузить на сервер')
        try:
            shutil.rmtree(os.path.join(save_path, channel_username))
        except:
            pass


async def fetch_all_messages(channel_username, postgram_link, postgram_account_link):
    try:
        async with client2:
            channel = await client2.get_entity(channel_username)
            offset_id = 0
            limit = 50
            while True:

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

                if not history.messages:
                    break

                if offset_id == 0:
                    last_date = history.messages[0].date

                message_info[channel_username] = []
                message_info_list = message_info[channel_username]
                for message in history.messages[::-1]:
                    try:
                        await save_message(channel_username, message, postgram_link, postgram_account_link, message_info_list, client2)
                    except:
                        print("ошибка при сохранении сообщения")
                try:
                    tasks = [asyncio.create_task(add_data_to_server(message, channel_username)) for message in message_info_list]
                    await asyncio.gather(*tasks)
                except:
                    print('ошибка, сообщение не удалось загрузить на сервер')
                try:
                    shutil.rmtree(os.path.join(save_path, channel_username))
                except:
                    pass


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

    except Exception as e:
        print(f'Не удалось получить сообщения: {e}')


async def save_message(channel_username, message, postgram_link, postgram_account_link, message_info, client):
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
                             'message_without_url': message.message,
                             'message_title_media': media_path,
                             'extra_media': [],
                             'channel_link': postgram_link,
                             'user_link': postgram_account_link,
                             'message_date': message.date + timedelta(hours=3)})
        if message.entities:
            offset_adjustment = 0
            for entity in message.entities:
                try:
                    if entity.document_id:
                        offset_adjustment -= entity.length - 1
                except:
                    pass
                try:
                    start = entity.offset + offset_adjustment - 1
                    end = start + entity.length + 1
                    link_html = f'<a href="{entity.url}">{message_info[-1]["message_text"][start:end]}</a>'
                    message_info[-1]['message_text'] = message_info[-1]['message_text'][:start] + link_html + message_info[-1]['message_text'][end:]
                    offset_adjustment += len(link_html) - entity.length
                except:
                    pass
        print(message_info[-1]['message_text'])
    else:
        if message_info:
            message_info[-1]['extra_media'].append(media_path)
