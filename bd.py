import aiosqlite
import os

DB_PATH = 'channels.db'

async def fetch_all_channels():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT * FROM channels')
        rows = await cursor.fetchall()
        for row in rows:
            print(row)

# Пример вызова функции
import asyncio
asyncio.run(fetch_all_channels())
