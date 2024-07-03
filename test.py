import mysql.connector
from mysql.connector import Error
from slugify import slugify
import re


def clean_search_string(input_string):
    # Оставляем только буквы, цифры и пробелы
    cleaned_string = re.sub(r'[^a-zA-Z0-9\s]', '', input_string)
    return cleaned_string


def func(host='db10.ipipe.ru', database='alexman_db1',
                                 user='alexman_db1', password='iGMqjTwJmwte'):
    try:
        connection = mysql.connector.connect(
            host=host,
            database=database,
            user=user,
            password=password
        )

        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)

            sql = "SELECT tag_id, name FROM tags WHERE 1"
            cursor.execute(sql)
            result = cursor.fetchall()

            if connection.is_connected():
                cursor.close()
                connection.close()

            for i in result:
                connection = mysql.connector.connect(
                    host=host,
                    database=database,
                    user=user,
                    password=password
                )

                tag_id = i['tag_id']
                tag_name = clean_search_string(slugify(i['name']))
                print(tag_name, tag_id)

                cursor = connection.cursor(dictionary=True)

                cursor.execute(sql, (tag_name, tag_id))
                connection.commit()

                if connection.is_connected():
                    cursor.close()
                    connection.close()
    except Error as e:
        print(e)

func()