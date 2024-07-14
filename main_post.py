import asyncio
import aiosqlite
from telegram_parser import fetch_messages, fetch_all_messages
from datetime import datetime

DB_PATH = 'channels.db'


async def check_new_messages():
    while True:
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                cursor = await db.execute('SELECT * FROM channels')
                channels = await cursor.fetchall()
                for channel in channels:
                    print(channel[1])
                    if channel[5] != -1:
                        await fetch_all_messages(channel[1], channel[2], channel[3], channel[5])
                    else:
                        await fetch_messages(channel[1], datetime.strptime(channel[4][:19], '%Y-%m-%d %H:%M:%S'), channel[2],
                                       channel[3])
        except:
            print('error')
        await asyncio.sleep(120)

if __name__ == '__main__':
    asyncio.run(check_new_messages())