from pwdlib import PasswordHash
password_hash = PasswordHash.recommended()
def hash_password(value: str) -> str: return password_hash.hash(value)
def verify_password(value: str, hashed: str) -> bool: return password_hash.verify(value, hashed)
