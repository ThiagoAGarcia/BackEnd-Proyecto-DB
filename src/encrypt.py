import bcrypt

def hash_pwd(password: str, rounds=16) -> bytes:
    pwd = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds))
    return pwd