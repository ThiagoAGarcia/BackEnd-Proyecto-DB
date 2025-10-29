import bcrypt
from typing import Tuple
from datetime import datetime

def hash_pwd(password: str, rounds=16) -> bytes:
    pwd = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds))
    return pwd