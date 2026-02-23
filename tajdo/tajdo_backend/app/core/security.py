from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
import bcrypt

from dotenv import load_dotenv
import os
import hashlib

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def verify_password(plain_password, hashed_password):
    # Pre-hash to ensure consistent length
    hashed_input = hashlib.sha256(plain_password.encode('utf-8')).hexdigest().encode('utf-8')
    # bcrypt.checkpw requires bytes
    return bcrypt.checkpw(hashed_input, hashed_password.encode('utf-8'))

def get_password_hash(password):
    # Pre-hash to ensure consistent length
    hashed_input = hashlib.sha256(password.encode('utf-8')).hexdigest().encode('utf-8')
    # bcrypt.hashpw returns bytes, we decode to store as string
    return bcrypt.hashpw(hashed_input, bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
