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
    
    print(f"🔍 Registering user: {username} with email: {email}")
    
    # Check if user already exists
    cursor.execute("SELECT * FROM users WHERE email=%s OR username=%s", (email, username))
    if cursor.fetchone():
        conn.close()
        print(f"❌ User already exists: {username}")
        return False  # Already exists
    
    # Encrypt password with ECC
    encrypted_password = ecc_encrypt(ECC_PUBLIC_KEY, password.encode())
    print(f"✅ Password encrypted successfully")
    
    try:
        # Try to insert with new schema (password_encrypted)
        cursor.execute("INSERT INTO users (username, email, password_encrypted) VALUES (%s, %s, %s)",
                       (username, email, encrypted_password))
        conn.commit()
        conn.close()
        print(f"✅ User {username} registered with ECC encryption")
        return True
    except Exception as e:
        # Only fallback to old schema if it's a schema issue, not a constraint issue
        if "password_hash" in str(e) or "password_encrypted" in str(e):
            print(f"Schema issue, trying old schema: {e}")
            try:
                cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                               (username, email, hash_password(password)))
                conn.commit()
                conn.close()
                print(f"✅ User {username} registered with hash (fallback)")
                return True
            except Exception as e2:
                print(f"Old schema also failed: {e2}")
                conn.close()
                return False
        else:
            # If it's a constraint violation (duplicate), don't fallback
            print(f"Registration failed: {e}")
            conn.close()
            return False

def validate_user(email, password):
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)  # Use DictCursor for named columns
    
    print(f"🔍 Validating user with email: {email}")
    
    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        print(f"✅ User found: {user['username']}")
        print(f"🔍 User has password_encrypted: {user.get('password_encrypted') is not None}")
        print(f"🔍 User has password_hash: {user.get('password_hash') is not None}")
        
        # Try new schema first (password_encrypted)
        if user.get('password_encrypted'):
            try:
                print("🔍 Attempting ECC decryption...")
                # Decrypt the stored password (it's already encrypted)
                decrypted_password = ecc_decrypt(ECC_PRIVATE_KEY, user['password_encrypted'])
                # Convert bytes to string for comparison
                decrypted_password_str = decrypted_password.decode('utf-8')
                
                print(f"🔍 Decrypted password: {decrypted_password_str}")
                print(f"🔍 Entered password: {password}")
                
                # Compare with the entered password
                if decrypted_password_str == password:
                    print("✅ Password match successful!")
                    return user
                else:
                    print("❌ Password mismatch")
                    return None
            except Exception as e:
                print(f"❌ ECC decryption error: {e}")
                return None
        
        # Fallback to old schema (password_hash) - for existing users
        elif user.get('password_hash'):
            print("🔍 Checking old password hash...")
            hashed_password = hash_password(password)
            print(f"🔍 Stored hash: {user['password_hash']}")
            print(f"🔍 Computed hash: {hashed_password}")
            if user['password_hash'] == hashed_password:
                print("✅ Old password hash match successful!")
                return user
            else:
                print("❌ Old password hash mismatch")
                return None
        else:
            print("❌ User has no password field")
            return None
    else:
        print(f"❌ User not found with email: {email}")
        return None
