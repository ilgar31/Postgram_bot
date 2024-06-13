import mysql.connector
from mysql.connector import Error
import json
import datetime
import paramiko
import os
import urllib.parse
import re
import uuid


def clean_search_string(input_string):
    # Оставляем только буквы, цифры и пробелы
    cleaned_string = re.sub(r'[^a-zA-Z0-9\s]', '', input_string)
    return cleaned_string


def get_user_id_and_community_id(username, communityname, host='alexmaxn.beget.tech', database='alexmaxn_hlam', user='alexmaxn_hlam', password='AM8lDUZNI8G%'):
    try:
        connection = mysql.connector.connect(
            host=host,
            database=database,
            user=user,
            password=password
        )

        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)

            sql1 = "SELECT id FROM users WHERE username = %s"
            cursor.execute(sql1, (username,))
            result1 = cursor.fetchone()

            sql2 = "SELECT id FROM communities WHERE slug = %s"
            cursor.execute(sql2, (communityname,))
            result2 = cursor.fetchone()

            if result1 and result2:
                return str(result1['id']), str(result2['id'])
            else:
                print("Пользователь не найден.")
                return None

    except Error as e:
        print(f"Ошибка при подключении к MySQL: {e}")
        return None

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("Соединение с MySQL закрыто.")


def get_tag(tag, host='alexmaxn.beget.tech', database='alexmaxn_hlam', user='alexmaxn_hlam', password='AM8lDUZNI8G%'):
    try:
        connection = mysql.connector.connect(
            host=host,
            database=database,
            user=user,
            password=password
        )

        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)

            sql = "SELECT tag_id FROM tags WHERE name = %s"
            cursor.execute(sql, (tag,))
            result = cursor.fetchone()

            if result:
                return str(result['tag_id'])
            else:
                return 0

    except Error as e:
        print(f"Ошибка при подключении к MySQL: {e}")
        return None

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("Соединение с MySQL закрыто.")


def upload_file_to_server(local_path, remote_path, hostname, port, username, password):
    try:
        transport = paramiko.Transport((hostname, port))
        transport.connect(username=username, password=password)

        sftp = paramiko.SFTPClient.from_transport(transport)

        remote_dir = os.path.dirname(remote_path)
        try:
            sftp.listdir(remote_dir)
        except IOError:
            print(f"Директория {remote_dir} не существует на сервере. Создание директории.")
            sftp.mkdir(remote_dir)


        sftp.put(local_path, remote_path)
        print(f"Файл {local_path} успешно загружен на {remote_path}")

        sftp.close()
        transport.close()
    except Exception as e:
        print(f"Ошибка при загрузке файла на сервер: {e}")


def insert_record(data, media_data, tags, image_path, host='alexmaxn.beget.tech', database='alexmaxn_hlam', user='alexmaxn_hlam', password='AM8lDUZNI8G%'):
    try:
        # Подключаемся к базе данных
        connection = mysql.connector.connect(
            host=host,
            database=database,
            user=user,
            password=password
        )

        if connection.is_connected():
            cursor = connection.cursor()

            # Формируем SQL-запрос для вставки данных
            placeholders = ', '.join(['%s'] * len(data))
            columns = ', '.join(data.keys())
            sql = f"INSERT INTO stories ({columns}) VALUES ({placeholders})"
            # Выполняем запрос
            cursor.execute(sql, tuple(data.values()))

            story_id = cursor.lastrowid

            connection.commit()
            print("Запись успешно добавлена в таблицу stories.")

            if media_data:
                media_data['model_id'] = story_id

                placeholders = ', '.join(['%s'] * len(media_data))
                columns = ', '.join(media_data.keys())
                sql = f"INSERT INTO media ({columns}) VALUES ({placeholders})"
                cursor.execute(sql, tuple(media_data.values()))

                upload_file_to_server(image_path, f'postgram.ru/public/uploads/stories/{cursor.lastrowid}/{media_data["file_name"]}', 'alexmaxn.beget.tech', 22, 'alexmaxn_2', password)

                connection.commit()
                print("Запись успешно добавлена в таблицу media.")

            if tags:
                for tag in tags:
                    tag = tag[1:]
                    tag_id = get_tag(tag)
                    if tag_id != 0:
                        placeholders = ', '.join(['%s'] * 5)
                        sql = f"INSERT INTO taggables (tag_id, taggable_id, taggable_type, created_at, updated_at) VALUES ({placeholders})"
                        cursor.execute(sql, (tag_id, story_id, 'App\\Models\\Story', data['created_at'], data['created_at']))
                        connection.commit()
                        print("Запись успешно добавлена в таблицу taggables.")
                    else:
                        placeholders = ', '.join(['%s'] * 4)
                        sql = f"INSERT INTO tags (name, normalized, created_at, updated_at) VALUES ({placeholders})"
                        cursor.execute(sql, (tag, clean_search_string(transliterate(tag)), data['created_at'], data['created_at']))
                        tag_id = cursor.lastrowid
                        connection.commit()
                        print("Запись успешно добавлена в таблицу tags.")

                        placeholders = ', '.join(['%s'] * 5)
                        sql = f"INSERT INTO taggables (tag_id, taggable_id, taggable_type, created_at, updated_at) VALUES ({placeholders})"
                        cursor.execute(sql, (tag_id, story_id, 'App\\Models\\Story', data['created_at'], data['created_at']))
                        connection.commit()
                        print("Запись успешно добавлена в таблицу taggables.")

    except Error as e:
        print(f"Ошибка при подключении к MySQL: {e}")

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("Соединение с MySQL закрыто.")



translit_table = str.maketrans({
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D',
    'Е': 'E', 'Ё': 'E', 'Ж': 'Zh', 'З': 'Z', 'И': 'I',
    'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N',
    'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T',
    'У': 'U', 'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch',
    'Ш': 'Sh', 'Щ': 'Shch', 'Ы': 'Y', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
    'е': 'e', 'ё': 'e', 'ж': 'zh', 'з': 'z', 'и': 'i',
    'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
    'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
    'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch',
    'ш': 'sh', 'щ': 'shch', 'ы': 'y', 'э': 'e', 'ю': 'yu', 'я': 'ya'
})

def transliterate(input_str):
    return input_str.translate(translit_table)


def add_data_to_server(message_info):
    data = {}
    media_data = {}
    tags_data = {}

    tags = list(filter(lambda x: x[0] == '#', message_info['message_text'].split()))
    for tag in tags:
        message_info['message_text'] = message_info['message_text'].replace(tag, '')



    user_name = urllib.parse.unquote(message_info['user_link']).split('/')[-1]
    channel_name = urllib.parse.unquote(message_info['channel_link']).split('/')[-1]
    user_id, community_id = get_user_id_and_community_id(user_name, channel_name)
    data['user_id'], data['community_id'] = user_id, community_id

    data['title'] = message_info['message_text'].split('\n')[0]
    data['subtitle'] = ''
    data['slug'] = clean_search_string(transliterate(data['title']))

    text = []
    for line in message_info['message_text'].split('\n'):
        if len(line) > 5:
            text.append(line)
    data['summary'] = (text[1][:70] + ' ...' if len(text[1]) > 71 else text[1]) if not('<a' in text[1]) else ''
    data['body'] = json.dumps({
        "time": int(message_info['message_date'].timestamp() * 1000),
        "version": "2.28.2",
    })
    data['body_rendered'] = '\n'.join(list(map(lambda x: f'<p class="w-content">{x}</p>', text)))
    data['published_at'] = message_info['message_date']
    data['created_at'] = message_info['message_date']

    if message_info['message_title_media']:
        media_data['model_type'] = 'App\\Models\\Story'
        media_data['uuid'] = str(uuid.uuid4())
        if os.path.basename(message_info['message_title_media']).split('.')[-1] == 'mp4':
            media_data['collection_name'] = 'featured-video'
        else:
            media_data['collection_name'] = 'featured-image'
        media_data['name'] = f"{channel_name}-{os.path.basename(message_info['message_title_media']).split('.')[0]}"
        media_data['file_name'] = f"{channel_name}-{os.path.basename(message_info['message_title_media'])}"
        media_data['mime_type'] = 'image/jpeg'
        media_data['disk'] = 'local'
        media_data['size'] = os.path.getsize(message_info['message_title_media'])
        media_data['manipulations'] = json.dumps([])
        media_data['custom_properties'] = json.dumps([])
        media_data['generated_conversions'] = json.dumps([])
        media_data['responsive_images'] = json.dumps([])
        media_data['order_column'] = 1

    insert_record(data, media_data, tags, message_info['message_title_media'])
