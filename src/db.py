import time
import pymysql
from config import config

MYSQL_HOST = config['development'].MYSQL_HOST
MYSQL_USER = config['development'].MYSQL_USER
MYSQL_PASSWORD = config['development'].MYSQL_PASSWORD
MYSQL_DB = config['development'].MYSQL_DB

connection = None

for attempt in range(10):
    try:
        connection = pymysql.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        print("✅ Conectado a MySQL")
        break
    except pymysql.err.OperationalError:
        print(f"⏳ MySQL no está listo, reintentando... ({attempt+1}/10)")
        time.sleep(3)

if connection is None:
    raise Exception("❌ No se pudo conectar a MySQL después de varios intentos")
