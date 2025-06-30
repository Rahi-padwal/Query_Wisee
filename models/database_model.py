import pymysql.cursors
from db_config import get_connection
from pymongo import MongoClient
from utils.crypto_utils import load_public_key, load_private_key, ecc_encrypt, ecc_decrypt

# ECC key loading (load once)
ECC_PUBLIC_KEY = load_public_key()
ECC_PRIVATE_KEY = load_private_key()

def get_user_databases(user_id):
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)  # ✅ This is the correct way in PyMySQL

    cursor.execute("SELECT * FROM databases_info WHERE user_id = %s", (user_id,))
    own = cursor.fetchall()

    cursor.execute("SELECT * FROM databases_info WHERE shared = 1 AND user_id != %s", (user_id,))
    shared = cursor.fetchall()

    conn.close()

    return {
        "own": own,
        "shared": shared
    }

def get_database_schema(db_name):
    print(f"\n=== Getting schema for database: {db_name} ===")
    
    # First connect to ai_sql_assistant to verify the database exists and get db_type and schema_json
    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM databases_info WHERE db_name = %s", (db_name,))
        db_info = cursor.fetchone()
        if not db_info:
            conn.close()
            raise Exception("Database not found")
        db_type = db_info.get('db_type')
        schema_json = db_info.get('schema_json')
        conn.close()
        
        print(f"Database type: {db_type}")
        print(f"Has schema_json: {bool(schema_json)}")
        
    except Exception as e:
        print(f"Error getting database info: {e}")
        raise Exception(f"Error getting database info: {str(e)}")

    if db_type == 'cloud' and schema_json:
        print("Processing cloud database...")
        import json
        return json.loads(schema_json)
    
    elif db_type == 'mongodb':
        print("Processing MongoDB database...")
        # Handle MongoDB databases
        try:
            # Simple test to see if MongoDB is running
            print("Testing basic MongoDB connectivity...")
            test_client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=3000)
            test_client.admin.command('ping')
            test_client.close()
            print("MongoDB is running and accessible")
            
            # Try different connection strings for different MongoDB setups
            connection_strings = [
                'mongodb://localhost:27017/',
                'mongodb://127.0.0.1:27017/',
                'mongodb://localhost:27017',
                'mongodb://127.0.0.1:27017'
            ]
            
            client = None
            for conn_str in connection_strings:
                try:
                    print(f"Trying MongoDB connection: {conn_str}")
                    client = MongoClient(conn_str, serverSelectionTimeoutMS=5000)
                    # Test the connection
                    client.admin.command('ping')
                    print(f"Successfully connected to MongoDB using: {conn_str}")
                    break
                except Exception as e:
                    print(f"Failed to connect with {conn_str}: {e}")
                    if client:
                        client.close()
                    continue
            
            if not client:
                raise Exception("Could not connect to MongoDB with any connection string")
            
            print(f"Connecting to MongoDB database: {db_name}")
            db = client[db_name]
            
            print("Getting collections...")
            collections = db.list_collection_names()
            print(f"Found collections: {collections}")
            
            if not collections:
                print("No collections found in database")
                client.close()
                return []
            
            schema = []
            for collection_name in collections:
                print(f"Processing collection: {collection_name}")
                collection = db[collection_name]
                
                # Get a sample document to understand the structure
                sample_doc = collection.find_one()
                
                if sample_doc:
                    columns = []
                    for field_name, field_value in sample_doc.items():
                        # Determine field type
                        if isinstance(field_value, str):
                            field_type = "string"
                        elif isinstance(field_value, int):
                            field_type = "integer"
                        elif isinstance(field_value, float):
                            field_type = "double"
                        elif isinstance(field_value, bool):
                            field_type = "boolean"
                        elif isinstance(field_value, dict):
                            field_type = "object"
                        elif isinstance(field_value, list):
                            field_type = "array"
                        else:
                            field_type = "mixed"
                        
                        columns.append({
                            'name': field_name,
                            'type': field_type
                        })
                    
                    schema.append({
                        'table_name': collection_name,
                        'columns': columns
                    })
                    print(f"Added collection {collection_name} with {len(columns)} fields")
                else:
                    print(f"Collection {collection_name} is empty")
            
            client.close()
            print(f"Final schema has {len(schema)} collections")
            return schema
            
        except Exception as e:
            print(f"Error getting MongoDB schema for {db_name}: {e}")
            import traceback
            traceback.print_exc()
            return []

    else:
        print("Processing MySQL database...")
        # Handle local MySQL databases
        try:
            conn = pymysql.connect(
                host="localhost",
                user="root",
                password="",
                database=db_name,  # Connect to the actual database
                cursorclass=pymysql.cursors.DictCursor
            )
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            # Get all tables in the database
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s
            """, (db_name,))
            tables = cursor.fetchall()
            schema = []
            for table in tables:
                table_name = table['TABLE_NAME']
                # Get columns for each table
                cursor.execute("""
                    SELECT column_name, data_type, character_maximum_length
                    FROM information_schema.columns 
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                """, (db_name, table_name))
                columns = cursor.fetchall()
                # Format column information
                column_info = []
                for col in columns:
                    col_type = col['DATA_TYPE']
                    if col['CHARACTER_MAXIMUM_LENGTH']:
                        col_type += f"({col['CHARACTER_MAXIMUM_LENGTH']})"
                    column_info.append({
                        'name': col['COLUMN_NAME'],
                        'type': col_type
                    })
                schema.append({
                    'table_name': table_name,
                    'columns': column_info
                })
            conn.close()
            return schema
        except Exception as e:
            print(f"Error getting MySQL schema for {db_name}: {e}")
            import traceback
            traceback.print_exc()
            return []

def import_database(user_id, db_name, db_type, schema_json=None, username=None, password=None):
    conn = get_connection()
    cursor = conn.cursor()

    # Check if it already exists
    cursor.execute("SELECT * FROM databases_info WHERE user_id = %s AND db_name = %s", (user_id, db_name))
    if cursor.fetchone():
        conn.close()
        raise Exception("Database already imported")

    # Encrypt credentials if provided (for all database types)
    username_encrypted = None
    password_encrypted = None
    
    if username and password:
        try:
            username_encrypted = ecc_encrypt(ECC_PUBLIC_KEY, username.encode())
            password_encrypted = ecc_encrypt(ECC_PUBLIC_KEY, password.encode())
            print(f"✅ Credentials encrypted for database: {db_name}")
        except Exception as e:
            print(f"❌ Failed to encrypt credentials: {e}")
            conn.close()
            raise Exception(f"Failed to encrypt credentials: {str(e)}")

    if schema_json is not None:
        cursor.execute("""
            INSERT INTO databases_info (user_id, db_name, db_type, schema_json, shared, created_at, db_username_encrypted, db_password_encrypted)
            VALUES (%s, %s, %s, %s, 0, NOW(), %s, %s)
        """, (user_id, db_name, db_type, schema_json, username_encrypted, password_encrypted))
    else:
        cursor.execute("""
            INSERT INTO databases_info (user_id, db_name, db_type, shared, created_at, db_username_encrypted, db_password_encrypted)
            VALUES (%s, %s, %s, 0, NOW(), %s, %s)
        """, (user_id, db_name, db_type, username_encrypted, password_encrypted))
    
    conn.commit()
    db_id = cursor.lastrowid
    conn.close()
    return db_id

def get_database_credentials(db_id):
    """Get decrypted credentials for a database"""
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    cursor.execute("SELECT db_username_encrypted, db_password_encrypted FROM databases_info WHERE db_id = %s", (db_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result and result.get('db_username_encrypted') and result.get('db_password_encrypted'):
        try:
            username = ecc_decrypt(ECC_PRIVATE_KEY, result['db_username_encrypted']).decode('utf-8')
            password = ecc_decrypt(ECC_PRIVATE_KEY, result['db_password_encrypted']).decode('utf-8')
            return {'username': username, 'password': password}
        except Exception as e:
            print(f"❌ Failed to decrypt credentials: {e}")
            return None
    
    return None

def delete_database(user_id, db_name):
    """Delete a database from databases_info by user_id and db_name."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM databases_info WHERE user_id = %s AND db_name = %s", (user_id, db_name))
            conn.commit()
            return cursor.rowcount
    finally:
        conn.close()
