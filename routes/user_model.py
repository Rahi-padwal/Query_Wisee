# user_model.py
from db_config import get_connection
from utils.crypto_utils import load_public_key, load_private_key, ecc_encrypt, ecc_decrypt
import pymysql.cursors
import hashlib

# ECC key loading (load once)
ECC_PUBLIC_KEY = load_public_key()
ECC_PRIVATE_KEY = load_private_key()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, email, password):
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)  # Use DictCursor for consistency
    
    # Check if user already exists
    cursor.execute("SELECT * FROM users WHERE email=%s OR username=%s", (email, username))
    if cursor.fetchone():
        conn.close()
        return False  # Already exists
    
    # Encrypt password with ECC
    encrypted_password = ecc_encrypt(ECC_PUBLIC_KEY, password.encode())
    
    try:
        # Try to insert with new schema (password_encrypted)
        cursor.execute("INSERT INTO users (username, email, password_encrypted) VALUES (%s, %s, %s)",
                       (username, email, encrypted_password))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        # Only fallback to old schema if it's a schema issue, not a constraint issue
        if "password_hash" in str(e) or "password_encrypted" in str(e):
            try:
                cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                               (username, email, hash_password(password)))
                conn.commit()
                conn.close()
                return True
            except Exception as e2:
                conn.close()
                return False
        else:
            # If it's a constraint violation (duplicate), don't fallback
            conn.close()
            return False

def validate_user(email, password):
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)  # Use DictCursor for named columns
    
    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        # Try new schema first (password_encrypted)
        if user.get('password_encrypted'):
            try:
                # Decrypt the stored password (it's already encrypted)
                decrypted_password = ecc_decrypt(ECC_PRIVATE_KEY, user['password_encrypted'])
                # Convert bytes to string for comparison
                decrypted_password_str = decrypted_password.decode('utf-8')
                
                # Compare with the entered password
                if decrypted_password_str == password:
                    return user
                else:
                    return None
            except Exception as e:
                return None
        
        # Fallback to old schema (password_hash) - for existing users
        elif user.get('password_hash'):
            hashed_password = hash_password(password)
            if user['password_hash'] == hashed_password:
                return user
            else:
                return None
        else:
            return None
    else:
        return None
