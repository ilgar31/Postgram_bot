import asyncssh
import aiomysql
import asyncio


async def get_user_id_and_community_id(username, communityname, host='db10.ipipe.ru', database='alexman_db1',
                                 user='alexman_db1', password='iGMqjTwJmwte'):

    connection = await aiomysql.connect(
        host=host,
        db=database,
        user=user,
        password=password
    )

    async with connection.cursor(aiomysql.DictCursor) as cursor:
        sql1 = "SELECT id FROM users WHERE username = %s"
        await cursor.execute(sql1, (username,))
        result1 = await cursor.fetchone()
        try:
            print(result1['id'])
        except:
            print("ошибка", username, communityname)

        sql2 = "SELECT id FROM communities WHERE slug = %s"
        await cursor.execute(sql2, (communityname,))
        result2 = await cursor.fetchone()
        try:
            print(result2['id'])
        except:
            print("ошибка", username, communityname)

        if result1 and result2:
            return str(result1['id']), str(result2['id'])
        else:
            print("Пользователь или сообщество не найдены.")
            return None


async def main():
    mas = [['Ильгар', 'testcommunity2'], ['Ильгар', 'testcommunity2'], ['Ильгар', 'testcommunity2'], ['Ильгар', 'testcommunity2'], ['Ильгар', 'testcommunity2']]
    tasks = [asyncio.create_task(get_user_id_and_community_id(a, b)) for a, b in mas]
    await asyncio.gather(*tasks)



if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())