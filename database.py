import sqlite3

def init_db():
    conn = sqlite3.connect('channels.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS channels
                      (id INTEGER PRIMARY KEY, channel_username TEXT UNIQUE)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS posts
                      (id INTEGER PRIMARY KEY, channel_id INTEGER, post_id INTEGER, content TEXT)''')
    conn.commit()
    conn.close()

def add_channel(channel_username):
    conn = sqlite3.connect('channels.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO channels (channel_username) VALUES (?)', (channel_username,))
    conn.commit()
    conn.close()

def add_post(channel_id, post_id, content):
    conn = sqlite3.connect('channels.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO posts (channel_id, post_id, content) VALUES (?, ?, ?)',
                   (channel_id, post_id, content))
    conn.commit()
    conn.close()

def get_channels():
    conn = sqlite3.connect('channels.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM channels')
    channels = cursor.fetchall()
    conn.close()
    return channels

def get_posts():
    conn = sqlite3.connect('channels.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM posts')
    posts = cursor.fetchall()
    conn.close()
    return posts

def print_channels():
    channels = get_channels()
    print("Channels:")
    for channel in channels:
        print(f"ID: {channel[0]}, Username: {channel[1]}")

def print_posts():
    posts = get_posts()
    print("Posts:")
    for post in posts:
        print(f"ID: {post[0]}, Channel ID: {post[1]}, Post ID: {post[2]}, Content: {post[3]}")