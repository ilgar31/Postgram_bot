import asyncio
import asyncssh
import aiomysql
import asyncio


async def add_tg_link(postgram_link, channel_username, host='db10.ipipe.ru', database='alexman_db1', user='alexman_db1', password='iGMqjTwJmwte'):
    try:
        connection = await aiomysql.connect(
            host=host,
            db=database,
            user=user,
            password=password
        )

        async with connection.cursor(aiomysql.DictCursor) as cursor:
            sql = "UPDATE communities SET tg_link = %s WHERE slug = %s"
            await cursor.execute(sql, ('https://t.me/' + channel_username, postgram_link.split('/')[-1]))

            await connection.commit()

    except Exception as e:
        print(e)

    finally:
        connection.close()


async def main():
    await add_tg_link('testcommunity2', 'hdfugvi')


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())