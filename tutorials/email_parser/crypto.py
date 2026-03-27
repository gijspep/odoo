import json
import os
import zipfile
from io import BytesIO

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=600_000)
    return kdf.derive(password.encode())


def encrypt_key(raw_key: bytes, password: str) -> tuple[bytes, bytes, bytes]:
    """Encrypt a raw AES key with a password. Returns (encrypted_key, salt, nonce)."""
    salt = os.urandom(16)
    nonce = os.urandom(12)
    derived = derive_key(password, salt)
    encrypted = AESGCM(derived).encrypt(nonce, raw_key, None)
    return encrypted, salt, nonce


def decrypt_key(encrypted: bytes, salt: bytes, nonce: bytes, password: str) -> bytes:
    """Decrypt a stored AES key using the original password. Raises on wrong password."""
    derived = derive_key(password, salt)
    return AESGCM(derived).decrypt(nonce, encrypted, None)


def encrypt_payload(key: bytes, file_bytes: bytes, filename: str) -> bytes:
    """Zip a file, then AES-GCM encrypt it. Returns nonce + ciphertext."""
    buf = BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(filename, file_bytes)
    zipped = buf.getvalue()
    nonce = os.urandom(12)
    return nonce + AESGCM(key).encrypt(nonce, zipped, None)


def decrypt_response(key: bytes, payload: bytes) -> dict:
    """AES-GCM decrypt a response payload, unzip it, and return the parsed JSON."""
    if len(payload) <= 12:
        raise ValueError("Payload too short to be valid.")
    nonce, ciphertext = payload[:12], payload[12:]
    decrypted = AESGCM(key).decrypt(nonce, ciphertext, None)
    with zipfile.ZipFile(BytesIO(decrypted), mode="r") as zf:
        names = zf.namelist()
        target = next((n for n in names if n.endswith(".json")), names[0])
        return json.loads(zf.read(target))
