from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import os, base64

# Load public key for encryption
def load_public_key(path="ecc_public_key.pem"):
    with open(path, "rb") as f:
        return serialization.load_pem_public_key(f.read())

# Load private key for decryption
def load_private_key(path="ecc_private_key.pem"):
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)

# Encrypt plaintext (bytes) with ECC public key
def ecc_encrypt(public_key, plaintext: bytes) -> str:
    # Generate ephemeral private key
    ephemeral_key = ec.generate_private_key(ec.SECP384R1())
    shared_key = ephemeral_key.exchange(ec.ECDH(), public_key)
    # Derive AES key
    derived_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b'ecc-encryption'
    ).derive(shared_key)
    # Encrypt with AES-GCM
    iv = os.urandom(12)
    encryptor = Cipher(
        algorithms.AES(derived_key),
        modes.GCM(iv)
    ).encryptor()
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    # Return ephemeral public key, iv, tag, ciphertext (all base64)
    return base64.b64encode(
        ephemeral_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ) + b'||' + iv + b'||' + encryptor.tag + b'||' + ciphertext
    ).decode()

# Decrypt ciphertext (str or bytes) with ECC private key
def ecc_decrypt(private_key, encrypted) -> bytes:
    # Handle both string and bytes input
    if isinstance(encrypted, bytes):
        # If it's already bytes, decode it as base64 string first
        encrypted_str = encrypted.decode('utf-8')
    else:
        # If it's a string, use it directly
        encrypted_str = encrypted
    
    decoded = base64.b64decode(encrypted_str.encode())
    pubkey_pem, iv, tag, ciphertext = decoded.split(b'||', 3)
    ephemeral_pubkey = serialization.load_pem_public_key(pubkey_pem)
    shared_key = private_key.exchange(ec.ECDH(), ephemeral_pubkey)
    derived_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b'ecc-encryption'
    ).derive(shared_key)
    decryptor = Cipher(
        algorithms.AES(derived_key),
        modes.GCM(iv, tag)
    ).decryptor()
    return decryptor.update(ciphertext) + decryptor.finalize() 