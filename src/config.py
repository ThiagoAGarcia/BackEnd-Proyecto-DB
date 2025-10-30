import os

class DevelopmentConfig:
    DEBUG = True
    MYSQL_HOST = os.getenv("MYSQL_HOST", "db")
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root")
    MYSQL_DB = os.getenv("MYSQL_DB", "ObligatorioBDD")

config = {
    'development': DevelopmentConfig
}
