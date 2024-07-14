import asyncio
import aiomysql
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def query_database(pool, query_num):
    retry_attempts = 3
    retry_delay = 5  # секунд
    for attempt in range(retry_attempts):
        try:
            async with pool.acquire() as connection:
                async with connection.cursor() as cursor:
                    await cursor.execute("SELECT * FROM contacts")
                    result = await cursor.fetchall()
                    logger.info(f"Запрос {query_num} завершён успешно.")
                    return result
        except Exception as e:
            logger.error(f"Ошибка при выполнении запроса {query_num}: {e}, попытка {attempt + 1} из {retry_attempts}")
            if attempt < retry_attempts - 1:
                await asyncio.sleep(retry_delay)
    return None

async def main():
    try:
        pool = await aiomysql.create_pool(
            host='db10.ipipe.ru',
            user='alexman_db1',
            password='iGMqjTwJmwte',
            db='alexman_db1',
            maxsize=100,  # Установите максимальный размер пула
            connect_timeout=2,  # Увеличьте таймаут соединения
        )
    except Exception as e:
        logger.error(f"Ошибка при создании пула соединений: {e}")
        return

    tasks = []
    for i in range(10):  # Пример сделать 10 запросов параллельно
        tasks.append(query_database(pool, i+1))

    try:
        results = await asyncio.gather(*tasks)
        logger.info(results)
        logger.info(f"Количество успешных результатов: {len([r for r in results if r is not None])}")
    except Exception as e:
        logger.error(f"Ошибка при выполнении запросов: {e}")
    finally:
        pool.close()
        await pool.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
