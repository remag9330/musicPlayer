import base64
import hashlib
import logging
from typing import Union

from database import database

def authenticate_user(username: str, password: str) -> Union[str, int]:
    user = database.get_user(username)
    if user is None:
        logging.info("Invalid username")
        return "invalidUsernameOrPassword"
    
    [expected_password_hash_b64, salt_b64, iterations_str] = user.password_hash.split(":")
    iterations = int(iterations_str)

    expected_password_hash = base64.b64decode(expected_password_hash_b64)
    salt = base64.b64decode(salt_b64)

    provided_password_hash = password_hash(password, salt, iterations)
    
    if expected_password_hash != provided_password_hash:
        logging.info("Invalid password")
        return "invalidUsernameOrPassword"
    
    return user.id
    
def password_hash(password: str, salt: bytes, iterations: int) -> bytes:
    n = iterations # iterations
    r = 8 # block size
    p = 1 # parallel
    maxmem = n * 2 * r * 65
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, maxmem=maxmem)