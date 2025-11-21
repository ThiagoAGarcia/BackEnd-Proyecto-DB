import time
import pymysql
from config import config

db_config = config['development']

def connection(role="unknown", retries=10, delay=3):
    creds = db_config.MYSQL_USERS.get(role)

    if not creds:
        raise ValueError(f"Rol de base de datos no soportado: {role}")

    for attempt in range(retries):
        try:
            conn = pymysql.connect(
                host=db_config.MYSQL_HOST,
                user=creds["user"],
                password=creds["password"],
                database=db_config.MYSQL_DB,
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
            )
            print(f"✅ Conectado a MySQL como {creds['user']} (rol app: {role})")
            return conn
        except pymysql.err.OperationalError as e:
            print(f"⏳ MySQL no está listo ({attempt+1}/{retries}) - error: {e}")
            time.sleep(delay)

    raise Exception("❌ No se pudo conectar a MySQL después de varios intentos")
