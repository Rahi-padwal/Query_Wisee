# db_config.py
import pymysql

def get_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="",
        database="ai_sql_assistant",  # your backend DB, not student_db
        cursorclass=pymysql.cursors.DictCursor
    )
