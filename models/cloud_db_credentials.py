import pymysql
from db_config import get_connection

def insert_cloud_db_credentials(db_id, host_url, username, password):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO cloud_db_credentials (db_id, host_url, username, password)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (db_id, host_url, username, password))
            conn.commit()
            return cursor.lastrowid
    finally:
        conn.close()

def get_cloud_db_credentials(db_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM cloud_db_credentials WHERE db_id = %s"
            cursor.execute(sql, (db_id,))
            return cursor.fetchone()
    finally:
        conn.close() 