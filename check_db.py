#!/usr/bin/env python3
"""
Simple script to check database registration and type
"""
import pymysql
from db_config import get_connection

def check_database():
    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Check all databases
        cursor.execute("SELECT * FROM databases_info WHERE db_name = 'ecommerce'")
        db_info = cursor.fetchone()
        
        if db_info:
            print("Database found:")
            print(f"  ID: {db_info['db_id']}")
            print(f"  Name: {db_info['db_name']}")
            print(f"  Type: {db_info['db_type']}")
            print(f"  User ID: {db_info['user_id']}")
            print(f"  Schema JSON: {db_info['schema_json'][:100] if db_info['schema_json'] else 'None'}...")
        else:
            print("Database 'ecommerce' not found in databases_info table")
            
            # Show all databases
            cursor.execute("SELECT db_name, db_type, user_id FROM databases_info")
            all_dbs = cursor.fetchall()
            print("\nAll registered databases:")
            for db in all_dbs:
                print(f"  {db['db_name']} (Type: {db['db_type']}, User: {db['user_id']})")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_database() 