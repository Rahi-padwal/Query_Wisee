import pymysql
import pymysql.cursors
from db_config import get_connection
from utils.crypto_utils import load_public_key, load_private_key, ecc_encrypt, ecc_decrypt

ECC_PUBLIC_KEY = load_public_key()
ECC_PRIVATE_KEY = load_private_key()

def insert_cloud_db_credentials(db_id, host_url, username, password):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Encrypt credentials
            host_url_enc = ecc_encrypt(ECC_PUBLIC_KEY, host_url.encode())
            username_enc = ecc_encrypt(ECC_PUBLIC_KEY, username.encode())
            password_enc = ecc_encrypt(ECC_PUBLIC_KEY, password.encode())
            sql = """
                INSERT INTO cloud_db_credentials (db_id, host_url_encrypted, username_encrypted, password_encrypted)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (db_id, host_url_enc, username_enc, password_enc))
            conn.commit()
            return cursor.lastrowid
    finally:
        conn.close()

def get_cloud_db_credentials(db_id):
    conn = get_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = "SELECT * FROM cloud_db_credentials WHERE db_id = %s"
            cursor.execute(sql, (db_id,))
            row = cursor.fetchone()
            if row:
                try:
                    # Decrypt credentials
                    row['host_url'] = ecc_decrypt(ECC_PRIVATE_KEY, row['host_url_encrypted']).decode() if row['host_url_encrypted'] else None
                    row['username'] = ecc_decrypt(ECC_PRIVATE_KEY, row['username_encrypted']).decode() if row['username_encrypted'] else None
                    row['password'] = ecc_decrypt(ECC_PRIVATE_KEY, row['password_encrypted']).decode() if row['password_encrypted'] else None
                    print(f"✅ Successfully decrypted credentials for db_id: {db_id}")
                except Exception as e:
                    print(f"❌ Error decrypting credentials for db_id {db_id}: {e}")
                    return None
            else:
                print(f"❌ No credentials found for db_id: {db_id}")
            return row
    except Exception as e:
        print(f"❌ Database error in get_cloud_db_credentials: {e}")
        return None
    finally:
        conn.close()

def delete_cloud_db_credentials(db_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM cloud_db_credentials WHERE db_id = %s", (db_id,))
            conn.commit()
            return cursor.rowcount
    finally:
        conn.close() 