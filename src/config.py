import os

class DevelopmentConfig:
    DEBUG = True
    MYSQL_HOST = os.getenv("MYSQL_HOST", "db")
    MYSQL_DB = os.getenv("MYSQL_DB", "ObligatorioBDD")

    MYSQL_USERS = {
        "unknown": {
            "user": os.getenv("MYSQL_UNKNOWN_USER", "unknown_user"),
            "password": os.getenv("MYSQL_UNKNOWN_PASSWORD", "Unknown19976543!"),
        },
        "student": {
            "user": os.getenv("MYSQL_STUDENT_USER", "student_user"),
            "password": os.getenv("MYSQL_STUDENT_PASSWORD", "Student19976543!"),
        },
        "professor": {
            "user": os.getenv("MYSQL_PROFESSOR_USER", "professor_user"),
            "password": os.getenv("MYSQL_PROFESSOR_PASSWORD", "Professor19976543!"),
        },
        "librarian": {
            "user": os.getenv("MYSQL_LIBRARIAN_USER", "librarian_user"),
            "password": os.getenv("MYSQL_LIBRARIAN_PASSWORD", "Librarian19976543!"),
        },
        "administrator": {
            "user": os.getenv("MYSQL_ADMIN_USER", "administrator_user"),
            "password": os.getenv("MYSQL_ADMIN_PASSWORD", "Admin19976543!"),
        },
    }

config = {
    "development": DevelopmentConfig
}
