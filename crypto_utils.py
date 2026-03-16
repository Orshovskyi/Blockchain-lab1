"""
Криптографічні засоби CNUCoin: хешування (MD5), ЕЦП (RSA).
Постійні для всієї системи.
"""
import hashlib
from typing import Tuple

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend


def hash_data(data: bytes) -> str:
    """Хеш-образ даних (MD5), повертає рядок у hex."""
    return hashlib.md5(data).hexdigest()


def generate_rsa_key_pair() -> Tuple[bytes, bytes]:
    """
    Генерує пару ключів RSA для ЕЦП.
    Повертає (private_key_pem, public_key_pem).
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def get_cnucoin_id(public_key_pem: bytes) -> str:
    """
    Ідентифікатор користувача CNUCoin = однократне хешування публічного ключа.
    Служить адресою в платіжній системі.
    """
    return hash_data(public_key_pem)


def sign_data(private_key_pem: bytes, data: bytes) -> bytes:
    """Підписує дані приватним ключем RSA (ЕЦП). Повертає підпис у бінарному вигляді."""
    private_key = serialization.load_pem_private_key(
        private_key_pem, password=None, backend=default_backend()
    )
    signature = private_key.sign(
        data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )
    return signature


def sign_data_hex(private_key_pem: bytes, data: bytes) -> str:
    """Підписує дані, повертає підпис у вигляді hex-рядка для збереження в БД."""
    return sign_data(private_key_pem, data).hex()


def verify_signature(public_key_pem: bytes, data: bytes, signature: bytes) -> bool:
    """Перевіряє ЕЦП за публічним ключем."""
    try:
        public_key = serialization.load_pem_public_key(
            public_key_pem, backend=default_backend()
        )
        public_key.verify(
            signature,
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False


def pem_to_storable(blob: bytes) -> str:
    """Перетворює PEM у рядок для збереження в БД (base64-подібний текст)."""
    return blob.decode("utf-8")
