import aiosqlite
import os

DB_PATH = 'channels.db'

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                user_id INTEGER,
                channel_username TEXT,
                channel_url TEXT,
                account_url TEXT,
                last_post_date TEXT DEFAULT NULL,
                history BOOL
            )
        ''')
        await db.commit()

# Пример вызова функции
import asyncio
asyncio.run(init_db())
