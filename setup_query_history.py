#!/usr/bin/env python3
"""
Setup script to create the query_history table in the database.
Run this script to set up the table for storing query history.
"""

import pymysql
from db_config import get_connection

def create_query_history_table():
    """Create the query_history table if it doesn't exist."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Create the query_history table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS query_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            db_name VARCHAR(255) NOT NULL,
            title VARCHAR(255) NOT NULL,
            query TEXT,
            natural_language TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_user_db (user_id, db_name),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        cursor.execute(create_table_sql)
        conn.commit()
        
        # Add foreign key constraint
        try:
            fk_sql = """
            ALTER TABLE query_history ADD CONSTRAINT fk_query_history_user 
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            """
            cursor.execute(fk_sql)
            conn.commit()
        except Exception as fk_error:
            pass
        
        # Check if table was created
        cursor.execute("SHOW TABLES LIKE 'query_history'")
        if cursor.fetchone():
            pass
        else:
            pass
            
        conn.close()
        
    except Exception as e:
        if conn:
            conn.close()

if __name__ == "__main__":
    create_query_history_table() 