import base64
import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

from settings import USERS_DIR

def authenticate_user(username: str, password: str) -> Optional[str]:
    user_file = Path(USERS_DIR) / Path(username)

    if not user_file.exists():
        logging.info("Invalid username")
        return "invalidUsernameOrPassword"
    
    with open(user_file, "r") as f:
        data = json.load(f)
    
    salt_b64 = str(data["password"]["salt"])
    expected_password_hash_b64 = str(data["password"]["hash"])
    iterations = int(data["password"]["iterations"])

    expected_password_hash = base64.b64decode(expected_password_hash_b64)
    salt = base64.b64decode(salt_b64)

    provided_password_hash = password_hash(password, salt, iterations)
    
    if expected_password_hash != provided_password_hash:
        logging.info("Invalid password")
        return "invalidUsernameOrPassword"
    
    return None
    
def password_hash(password: str, salt: bytes, iterations: int) -> bytes:
    n = iterations # iterations
    r = 8 # block size
    p = 1 # parallel
    maxmem = n * 2 * r * 65
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, maxmem=maxmem)