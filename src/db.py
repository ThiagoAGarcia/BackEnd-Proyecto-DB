import time
import pymysql
from config import config

db_config = config['development']

def connection(retries=10, delay=3):
    for attempt in range(retries):
        try:
            connection = pymysql.connect(
                host=db_config.MYSQL_HOST,
                user=db_config.MYSQL_USER,
                password=db_config.MYSQL_PASSWORD,
                database=db_config.MYSQL_DB,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            print("✅ Conectado a MySQL")
            return connection
        except pymysql.err.OperationalError as e:
            print(f"⏳ MySQL no está listo, reintentando... ({attempt+1}/{retries})")
            time.sleep(delay)
    raise Exception("❌ No se pudo conectar a MySQL después de varios intentos")
