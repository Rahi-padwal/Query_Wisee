# routes/db_routes.py
from flask import Blueprint, request, jsonify
from models.database_model import get_user_databases, import_database, get_database_schema, get_database_credentials, delete_database
from utils.prompt_generator import (
    generate_english_to_sql_prompt, 
    generate_sql_to_english_prompt,
    generate_english_to_mongodb_prompt,
    generate_mongodb_to_english_prompt,
    generate_workspace_mongodb_prompt
)
import requests
import pymysql
from db_config import get_connection
from config import GROQ_API_KEY
from models.cloud_db_credentials import insert_cloud_db_credentials, get_cloud_db_credentials, delete_cloud_db_credentials
import json
from pymongo import MongoClient

db_routes = Blueprint('db_routes', __name__)

@db_routes.route('/get-databases', methods=['GET'])
def get_databases():
    user_id = request.args.get('user_id')
    try:
        data = get_user_databases(user_id)
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@db_routes.route('/get-database-type', methods=['GET'])
def get_database_type():
    db_name = request.args.get('db_name')
    
    if not db_name:
        return jsonify({"error": "Database name is required"}), 400
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM databases_info WHERE db_name = %s", (db_name,))
        count_result = cursor.fetchone()
        
        cursor.execute("SELECT db_type FROM databases_info WHERE db_name = %s", (db_name,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return jsonify({"error": "Database not found"}), 404
        
        db_type = result['db_type']
        return jsonify({"db_type": db_type}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@db_routes.route('/get-schema', methods=['GET'])
def get_schema():
    db_name = request.args.get('db_name')
    if not db_name:
        return jsonify({"error": "Database name is required"}), 400
    
    try:
        schema = get_database_schema(db_name)
        return jsonify(schema), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@db_routes.route('/import-database', methods=['POST'])
def import_db():
    data = request.get_json()
    user_id = data['user_id']
    db_name = data['db_name']
    db_type = data.get('db_type', 'local')
    username = data.get('username')
    password = data.get('password')

    try:
        schema = get_database_schema(db_name)
        schema_json = json.dumps(schema) if schema else None
        
        import_database(user_id, db_name, db_type, schema_json, username, password)
        return jsonify({"message": "Database imported successfully."}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@db_routes.route('/convert-to-sql', methods=['POST'])
def convert_to_sql():
    try:
        if not GROQ_API_KEY:
            return jsonify({"error": "GROQ_API_KEY is not configured. Please set your Groq API key in the .env file or environment variables."}), 500

        try:
            data = request.get_json()
        except Exception as e:
            return jsonify({"error": f"Error parsing request data: {str(e)}"}), 400
            
        english = data.get('prompt')
        db_name = data.get('dbName')
        schema = data.get('schema')
        
        print(f"=== Convert to SQL Debug ===")
        print(f"English prompt: {english}")
        print(f"Database name: {db_name}")
        print(f"Schema: {schema}")
        
        if not english or not db_name or not schema:
            return jsonify({"error": "Missing required data"}), 400

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT db_type FROM databases_info WHERE db_name = %s", (db_name,))
            result = cursor.fetchone()
            db_type = result['db_type'] if result else 'mysql'
            conn.close()
            print(f"Detected database type: {db_type}")
        except Exception as e:
            db_type = 'mysql'
            print(f"Error getting database type, defaulting to mysql: {e}")
            
        try:
            if db_type.lower() == 'mongodb':
                print(f"Generating English to MongoDB prompt for: {english}")
                prompt = generate_english_to_mongodb_prompt(english, schema)
                system_content = "You are a MongoDB expert that converts English descriptions to MongoDB queries. Provide only the MongoDB query without any explanation."
            else:
                print(f"Generating English to SQL prompt for: {english}")
                prompt = generate_english_to_sql_prompt(english, schema)
                system_content = "You are a SQL expert that converts English descriptions to SQL queries. Provide only the SQL query without any explanation."
            
            print(f"Generated prompt: {prompt}")
        except Exception as e:
            print(f"Error generating prompt: {e}")
            import traceback
            traceback.print_exc()
            # Use fallback conversion
            if db_type.lower() == 'mongodb':
                query = convert_english_to_mongodb(english, schema)
            else:
                query = convert_english_to_sql(english, schema)
            return jsonify({"query": query}), 200
        
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        request_body = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 200,
            "top_p": 1,
            "stream": False
        }
        
        print(f"Sending request to Groq API...")
        try:
            response = requests.post('https://api.groq.com/openai/v1/chat/completions',
                headers=headers,
                json=request_body,
                timeout=30
            )
            print(f"Groq API response status: {response.status_code}")
            print(f"Groq API response: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error making request to Groq API: {e}")
            # Use fallback conversion
            if db_type.lower() == 'mongodb':
                query = convert_english_to_mongodb(english, schema)
            else:
                query = convert_english_to_sql(english, schema)
            return jsonify({"query": query}), 200

        if response.status_code == 401:
            return jsonify({"error": "Invalid Groq API key. Please check your API key configuration."}), 500
        elif response.status_code == 429:
            return jsonify({"error": "Rate limit exceeded. Please try again later."}), 500
        elif response.status_code != 200:
            print(f"Groq API error: {response.status_code} - {response.text}")
            # Use fallback conversion
            if db_type.lower() == 'mongodb':
                query = convert_english_to_mongodb(english, schema)
            else:
                query = convert_english_to_sql(english, schema)
            return jsonify({"query": query}), 200

        try:
            response_data = response.json()
            print(f"Response data: {response_data}")
            
            if 'choices' not in response_data or not response_data['choices']:
                print("No choices in response, using fallback")
                # Use fallback conversion
                if db_type.lower() == 'mongodb':
                    query = convert_english_to_mongodb(english, schema)
                else:
                    query = convert_english_to_sql(english, schema)
                return jsonify({"query": query}), 200

            query = response_data['choices'][0]['message']['content'].strip()
            print(f"Generated query: {query}")
            
            # Check if query is empty or contains error indicators
            if not query or query.lower() in ['no query generated', 'error', 'failed']:
                print("Query is empty or contains error, using fallback")
                # Use fallback conversion
                if db_type.lower() == 'mongodb':
                    query = convert_english_to_mongodb(english, schema)
                else:
                    query = convert_english_to_sql(english, schema)
            
            return jsonify({"query": query}), 200
        except (KeyError, IndexError) as e:
            print(f"Error parsing Groq API response: {e}")
            # Use fallback conversion
            if db_type.lower() == 'mongodb':
                query = convert_english_to_mongodb(english, schema)
            else:
                query = convert_english_to_sql(english, schema)
            return jsonify({"query": query}), 200
            
    except Exception as e:
        print(f"Unexpected error in convert-to-sql: {e}")
        import traceback
        traceback.print_exc()
        # Use fallback conversion
        try:
            if db_type.lower() == 'mongodb':
                query = convert_english_to_mongodb(english, schema)
            else:
                query = convert_english_to_sql(english, schema)
            return jsonify({"query": query}), 200
        except:
            return jsonify({"error": f"Error in /convert-to-sql: {str(e)}"}), 500

def convert_english_to_mongodb(english_query, schema):
    """Simple English to MongoDB conversion with schema awareness"""
    query_lower = english_query.lower()
    
    # Get the first collection from schema
    collection_name = schema[0]['table_name'] if schema else 'collection'
    
    # Basic patterns for MongoDB conversion
    if any(word in query_lower for word in ['find', 'get', 'show', 'display', 'list', 'select']):
        if 'all' in query_lower or 'every' in query_lower:
            return f"db.{collection_name}.find()"
        else:
            return f"db.{collection_name}.find({{}})"
    elif any(word in query_lower for word in ['insert', 'add', 'create']):
        return f"db.{collection_name}.insertOne({{}})"
    elif any(word in query_lower for word in ['update', 'modify', 'change']):
        return f"db.{collection_name}.updateOne({{}}, {{$set: {{}}}})"
    elif any(word in query_lower for word in ['delete', 'remove']):
        return f"db.{collection_name}.deleteOne({{}})"
    else:
        return f"db.{collection_name}.find()"

def convert_english_to_sql(english_query, schema):
    """Simple English to SQL conversion with schema awareness"""
    query_lower = english_query.lower()
    
    # Get the first table from schema
    table_name = schema[0]['table_name'] if schema else 'table_name'
    
    # Basic patterns for SQL conversion
    if any(word in query_lower for word in ['find', 'get', 'show', 'display', 'list', 'select']):
        if 'all' in query_lower or 'every' in query_lower:
            return f"SELECT * FROM {table_name}"
        else:
            return f"SELECT * FROM {table_name} WHERE condition"
    elif any(word in query_lower for word in ['insert', 'add', 'create']):
        return f"INSERT INTO {table_name} (column1, column2) VALUES (value1, value2)"
    elif any(word in query_lower for word in ['update', 'modify', 'change']):
        return f"UPDATE {table_name} SET column1 = value1 WHERE condition"
    elif any(word in query_lower for word in ['delete', 'remove']):
        return f"DELETE FROM {table_name} WHERE condition"
    else:
        return f"SELECT * FROM {table_name}"

@db_routes.route('/convert-to-english', methods=['POST'])
def convert_to_english():
    try:
        if not GROQ_API_KEY:
            return jsonify({"error": "GROQ_API_KEY is not configured. Please set your Groq API key in the .env file or environment variables."}), 500

        try:
            data = request.get_json()
        except Exception as e:
            return jsonify({"error": f"Error parsing request data: {str(e)}"}), 400
            
        query = data.get('prompt')
        db_name = data.get('dbName')
        schema = data.get('schema')
        
        if not query or not db_name or not schema:
            return jsonify({"error": "Missing required data"}), 400

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT db_type FROM databases_info WHERE db_name = %s", (db_name,))
            result = cursor.fetchone()
            db_type = result['db_type'] if result else 'mysql'
            conn.close()
            print(f"Detected database type: {db_type}")
        except Exception as e:
            db_type = 'mysql'
            print(f"Error getting database type, defaulting to mysql: {e}")
            
        try:
            if db_type.lower() == 'mongodb':
                print(f"Generating MongoDB to English prompt for query: {query}")
                prompt = generate_mongodb_to_english_prompt(query, schema)
                system_content = "You are a MongoDB expert that explains MongoDB queries in plain English. Provide a clear and concise explanation of what the MongoDB query does."
            else:
                print(f"Generating SQL to English prompt for query: {query}")
                prompt = generate_sql_to_english_prompt(query, schema)
                system_content = "You are a SQL expert that explains SQL queries in plain English. Provide a clear and concise explanation of what the SQL query does."
        except Exception as e:
            print(f"Error generating prompt: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"Error generating prompt: {str(e)}"}), 500
        
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        request_body = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 200,
            "top_p": 1,
            "stream": False
        }
        
        try:
            response = requests.post('https://api.groq.com/openai/v1/chat/completions',
                headers=headers,
                json=request_body,
                timeout=30
            )
        except requests.exceptions.RequestException as e:
            return jsonify({"error": f"Error making request to Groq API: {str(e)}"}), 500

        if response.status_code == 401:
            return jsonify({"error": "Invalid Groq API key. Please check your API key configuration."}), 500
        elif response.status_code == 429:
            return jsonify({"error": "Rate limit exceeded. Please try again later."}), 500
        elif response.status_code != 200:
            return jsonify({"error": f"Failed to get response from Groq API. Status code: {response.status_code}"}), 500

        try:
            response_data = response.json()
            
            if 'choices' not in response_data or not response_data['choices']:
                return jsonify({"error": "Invalid response format from Groq API"}), 500

            english_description = response_data['choices'][0]['message']['content'].strip()
            
            return jsonify({"english": english_description}), 200
        except (KeyError, IndexError) as e:
            return jsonify({"error": f"Error parsing Groq API response: {str(e)}"}), 500
            
    except Exception as e:
        return jsonify({"error": f"Error in /convert-to-english: {str(e)}"}), 500

def convert_mongodb_to_english(query):
    """Simple MongoDB to English conversion"""
    query_lower = query.lower().strip()
    
    if query_lower.startswith('db.'):
        parts = query.split('.')
        if len(parts) >= 3:
            collection_name = parts[1]
            operation_part = '.'.join(parts[2:])
            
            if 'find(' in operation_part:
                if 'find()' in operation_part or 'find({})' in operation_part:
                    return f"Find all documents in the {collection_name} collection"
                else:
                    return f"Find documents in the {collection_name} collection with specific criteria"
            elif 'insert(' in operation_part or 'insertone(' in operation_part:
                return f"Insert a new document into the {collection_name} collection"
            elif 'update(' in operation_part or 'updateone(' in operation_part:
                return f"Update documents in the {collection_name} collection"
            elif 'delete(' in operation_part or 'deleteone(' in operation_part:
                return f"Delete documents from the {collection_name} collection"
            else:
                return f"Perform operation on the {collection_name} collection"
    
    return f"Execute MongoDB query: {query}"

def convert_sql_to_english(query):
    """Simple SQL to English conversion"""
    query_lower = query.lower().strip()
    
    if query_lower.startswith('select'):
        if 'from' in query_lower:
            # Extract table name
            from_index = query_lower.find('from')
            table_part = query_lower[from_index:].split()[1]
            table_name = table_part.strip(';')
            
            if 'where' in query_lower:
                return f"Select data from {table_name} table with specific conditions"
            else:
                return f"Select all data from {table_name} table"
        else:
            return "Select data from database"
    elif query_lower.startswith('insert'):
        return "Insert new data into database"
    elif query_lower.startswith('update'):
        return "Update existing data in database"
    elif query_lower.startswith('delete'):
        return "Delete data from database"
    elif query_lower.startswith('create'):
        return "Create new table or database structure"
    elif query_lower.startswith('alter'):
        return "Modify existing table structure"
    elif query_lower.startswith('drop'):
        return "Remove table or database structure"
    else:
        return f"Execute SQL query: {query}"

@db_routes.route('/execute-query', methods=['POST'])
def execute_query():
    try:
        print("=== Starting execute_query ===")
        data = request.get_json()
        
        db_name = data.get('dbName')
        query = data.get('query')
        user_id = data.get('user_id')

        print(f"Received data - db_name: {db_name}, user_id: {user_id}, query: {query}")

        if not db_name or not query:
            return jsonify({"error": "Missing database name or query"}), 400

        # Debug logging
        print(f"Executing query for database: {db_name}, user_id: {user_id}")
        print(f"Query: {query}")

        try:
            conn = get_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            if user_id:
                cursor.execute("SELECT db_id, db_type FROM databases_info WHERE db_name = %s AND user_id = %s", (db_name, user_id))
            else:
                cursor.execute("SELECT db_id, db_type FROM databases_info WHERE db_name = %s", (db_name,))
                
            db_info = cursor.fetchone()
            conn.close()

            if not db_info:
                return jsonify({"error": f"Database '{db_name}' not found or access denied"}), 400

            print(f"Database info: {db_info}")
            print(f"Database type: {db_info.get('db_type', 'unknown')}")
        except Exception as e:
            print(f"Error getting database info: {e}")
            return jsonify({"error": f"Error getting database info: {str(e)}"}), 500

        if db_info['db_type'] == 'mongodb':
            try:
                print("Connecting to MongoDB...")
                
                # For MongoDB, try to connect directly to local MongoDB since no credentials are needed
                print("Connecting to local MongoDB (no authentication required)...")
                try:
                    # Connect to local MongoDB
                    client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
                    # Test the connection
                    client.admin.command('ping')
                    print("Successfully connected to local MongoDB")
                    
                    # Check if database exists
                    if db_name not in client.list_database_names():
                        return jsonify({"error": f"MongoDB database '{db_name}' not found on local server"}), 400
                    
                    db = client[db_name]
                    print(f"Connected to database: {db_name}")
                    
                    # For local MongoDB, allow all operations
                    print("Executing MongoDB query on local database...")
                    print(f"Query: {query}")
                    
                    if query.startswith('db.'):
                        parts = query.split('.')
                        if len(parts) >= 3:
                            collection_name = parts[1]
                            operation_part = '.'.join(parts[2:])
                            print(f"Collection: {collection_name}, Operation: {operation_part}")
                            
                            # Check if collection exists
                            if collection_name not in db.list_collection_names():
                                return jsonify({"error": f"Collection '{collection_name}' not found in database '{db_name}'"}), 400
                            
                            collection = db[collection_name]
                            print(f"Connected to collection: {collection_name}")
                            
                            # Handle different MongoDB operations for local database
                            if 'find(' in operation_part:
                                start_idx = operation_part.find('(') + 1
                                end_idx = operation_part.rfind(')')
                                if end_idx >= start_idx:
                                    filter_str = operation_part[start_idx:end_idx].strip()
                                    try:
                                        # If filter_str is empty, use empty dict
                                        if not filter_str:
                                            filter_doc = {}
                                        else:
                                            filter_doc = json.loads(filter_str)
                                        results = list(collection.find(filter_doc))
                                        
                                        if results:
                                            columns = list(results[0].keys())
                                            rows = []
                                            for doc in results:
                                                row = {}
                                                for col in columns:
                                                    row[col] = str(doc.get(col, ''))
                                                rows.append(row)
                                        else:
                                            columns = ["message"]
                                            rows = [{"message": "No documents found"}]
                                        
                                        client.close()
                                        return jsonify({
                                            "columns": columns,
                                            "rows": rows,
                                            "operation": "find",
                                            "affected_rows": len(rows)
                                        }), 200
                                    except json.JSONDecodeError:
                                        return jsonify({"error": "Invalid JSON format for find operation"}), 400
                                else:
                                    return jsonify({"error": "Invalid find operation format"}), 400
                            elif 'insert(' in operation_part or 'insertOne(' in operation_part:
                                # Handle insert operation
                                start_idx = operation_part.find('(') + 1
                                end_idx = operation_part.rfind(')')
                                if end_idx > start_idx:
                                    doc_data = operation_part[start_idx:end_idx].strip()
                                    print(f"Document data: {doc_data}")
                                    try:
                                        document = json.loads(doc_data)
                                        print(f"Document to insert: {document}")
                                        result = collection.insert_one(document)
                                        client.close()
                                        return jsonify({
                                            "columns": ["inserted_id"],
                                            "rows": [{"inserted_id": str(result.inserted_id)}],
                                            "operation": "insert",
                                            "affected_rows": 1,
                                            "message": f"Document inserted successfully with ID: {result.inserted_id}"
                                        }), 200
                                    except json.JSONDecodeError as e:
                                        print(f"JSON decode error: {e}")
                                        return jsonify({"error": f"Invalid JSON format for insert operation: {str(e)}"}), 400
                                else:
                                    return jsonify({"error": "Invalid insert operation format"}), 400
                            elif 'update(' in operation_part or 'updateOne(' in operation_part or 'updateMany(' in operation_part:
                                # Handle update operation
                                start_idx = operation_part.find('(') + 1
                                end_idx = operation_part.rfind(')')
                                if end_idx > start_idx:
                                    update_str = operation_part[start_idx:end_idx].strip()
                                    print(f"Update string: {update_str}")
                                    try:
                                        parts = update_str.split(',', 1)
                                        if len(parts) == 2:
                                            filter_str = parts[0].strip()
                                            update_str = parts[1].strip()
                                            filter_doc = json.loads(filter_str)
                                            update_doc = json.loads(update_str)
                                            print(f"Filter: {filter_doc}, Update: {update_doc}")
                                            
                                            if 'updateOne' in operation_part:
                                                result = collection.update_one(filter_doc, {'$set': update_doc})
                                            else:
                                                result = collection.update_many(filter_doc, {'$set': update_doc})
                                                
                                            client.close()
                                            return jsonify({
                                                "columns": ["modified_count"],
                                                "rows": [{"modified_count": result.modified_count}],
                                                "operation": "update",
                                                "affected_rows": result.modified_count,
                                                "message": f"Updated {result.modified_count} document(s)"
                                            }), 200
                                        else:
                                            return jsonify({"error": "Invalid update operation format"}), 400
                                    except json.JSONDecodeError as e:
                                        print(f"JSON decode error: {e}")
                                        return jsonify({"error": f"Invalid JSON format for update operation: {str(e)}"}), 400
                                else:
                                    return jsonify({"error": "Invalid update operation format"}), 400
                            elif 'delete(' in operation_part or 'deleteOne(' in operation_part or 'deleteMany(' in operation_part:
                                # Handle delete operation
                                start_idx = operation_part.find('(') + 1
                                end_idx = operation_part.rfind(')')
                                if end_idx > start_idx:
                                    filter_str = operation_part[start_idx:end_idx].strip()
                                    print(f"Delete filter: {filter_str}")
                                    try:
                                        filter_doc = json.loads(filter_str)
                                        print(f"Filter document: {filter_doc}")
                                        
                                        if 'deleteOne' in operation_part:
                                            result = collection.delete_one(filter_doc)
                                        else:
                                            result = collection.delete_many(filter_doc)
                                            
                                        client.close()
                                        return jsonify({
                                            "columns": ["deleted_count"],
                                            "rows": [{"deleted_count": result.deleted_count}],
                                            "operation": "delete",
                                            "affected_rows": result.deleted_count,
                                            "message": f"Deleted {result.deleted_count} document(s)"
                                        }), 200
                                    except json.JSONDecodeError as e:
                                        print(f"JSON decode error: {e}")
                                        return jsonify({"error": f"Invalid JSON format for delete operation: {str(e)}"}), 400
                                else:
                                    return jsonify({"error": "Invalid delete operation format"}), 400
                            else:
                                return jsonify({"error": "Unsupported MongoDB operation. Supported: find, insert, update, delete"}), 400
                        else:
                            return jsonify({"error": "Invalid MongoDB query format. Use: db.collection.operation()"}), 400
                    else:
                        return jsonify({"error": "MongoDB queries must start with 'db.'"}), 400
                except Exception as e:
                    print(f"Error connecting to local MongoDB: {e}")
                    return jsonify({"error": f"Failed to connect to local MongoDB: {str(e)}"}), 400
            except Exception as e:
                print(f"Error in MongoDB execution: {e}")
                return jsonify({"error": f"MongoDB error: {str(e)}"}), 500
                
        elif db_info['db_type'] == 'cloud':
            try:
                print("Connecting to cloud MySQL database...")
                creds = get_cloud_db_credentials(db_info['db_id'])
                
                if not creds:
                    return jsonify({"error": f"Cloud DB credentials not found for database ID: {db_info['db_id']}"}), 500
                
                conn = pymysql.connect(
                    host=creds['host_url'],
                    user=creds['username'],
                    password=creds['password'],
                    database=db_name,
                    cursorclass=pymysql.cursors.DictCursor,
                    autocommit=False,
                    connect_timeout=30,
                    read_timeout=30,
                    write_timeout=30
                )
                
                print("Connected to cloud MySQL database successfully")
                
                cursor = conn.cursor()
                
                # Check if query is a modification query for cloud databases
                query_lower = query.strip().lower()
                if any(keyword in query_lower for keyword in ['insert', 'update', 'delete', 'drop', 'create', 'alter', 'truncate']):
                    conn.close()
                    return jsonify({
                        "error": "Modification queries are not allowed on cloud databases for security reasons.",
                        "blocked_operation": True,
                        "message": "This operation is blocked to protect your cloud database."
                    }), 403

                print("Executing MySQL query on cloud database...")
                cursor.execute(query)
                
                if query_lower.startswith('select'):
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    rows = cursor.fetchall()
                    
                    conn.commit()
                    conn.close()
                    
                    response_data = {
                        "columns": columns,
                        "rows": rows,
                        "operation": "select",
                        "affected_rows": len(rows)
                    }
                    
                    print(f"Cloud MySQL SELECT query executed successfully, result count: {len(rows)}")
                    print(f"Response data being sent: {response_data}")
                    return jsonify(response_data), 200
                else:
                    conn.commit()
                    conn.close()
                    print("Cloud MySQL query executed successfully")
                    return jsonify({
                        "columns": ["status"],
                        "rows": [{"status": "success"}],
                        "operation": "other",
                        "affected_rows": cursor.rowcount,
                        "message": "Query executed successfully."
                    }), 200
                    
            except Exception as e:
                print(f"Error in cloud MySQL execution: {e}")
                try:
                    conn.rollback()
                    conn.close()
                except:
                    pass
                return jsonify({"error": f"Cloud MySQL error: {str(e)}"}), 500
        else:
            try:
                print("Connecting to local MySQL database...")
                # For local databases, we don't need cloud credentials
                # Just connect directly to the local database
                conn = pymysql.connect(
                    host="localhost",
                    user="root",
                    password="",
                    database=db_name,
                    cursorclass=pymysql.cursors.DictCursor,
                    autocommit=False
                )
                
                print("Connected to local MySQL database successfully")
                
                cursor = conn.cursor()
                
                # For local databases, allow all types of queries
                print("Executing MySQL query on local database...")
                cursor.execute(query)
                
                query_lower = query.strip().lower()
                
                if query_lower.startswith('select'):
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    rows = cursor.fetchall()
                    
                    conn.commit()
                    conn.close()
                    
                    print(f"Local MySQL SELECT query executed successfully, result count: {len(rows)}")
                    return jsonify({
                        "columns": columns,
                        "rows": rows,
                        "operation": "select",
                        "affected_rows": len(rows)
                    }), 200
                    
                elif any(query_lower.startswith(op) for op in ['insert', 'update', 'delete']):
                    affected_rows = cursor.rowcount
                    
                    conn.commit()
                    conn.close()
                    
                    operation = "insert" if query_lower.startswith('insert') else "update" if query_lower.startswith('update') else "delete"
                    
                    print(f"Local MySQL {operation.upper()} query executed successfully, affected rows: {affected_rows}")
                    return jsonify({
                        "columns": ["affected_rows"],
                        "rows": [{"affected_rows": affected_rows}],
                        "operation": operation,
                        "affected_rows": affected_rows,
                        "message": f"{operation.capitalize()} operation completed. {affected_rows} row(s) affected."
                    }), 200
                    
                elif any(query_lower.startswith(op) for op in ['create', 'alter', 'drop', 'truncate']):
                    conn.commit()
                    conn.close()
                    
                    operation = "create" if query_lower.startswith('create') else "alter" if query_lower.startswith('alter') else "drop" if query_lower.startswith('drop') else "truncate"
                    
                    print(f"Local MySQL {operation.upper()} query executed successfully")
                    return jsonify({
                        "columns": ["status"],
                        "rows": [{"status": "success"}],
                        "operation": operation,
                        "affected_rows": 0,
                        "message": f"{operation.capitalize()} operation completed successfully."
                    }), 200
                else:
                    conn.commit()
                    conn.close()
                    print("Local MySQL query executed successfully")
                    return jsonify({
                        "columns": ["status"],
                        "rows": [{"status": "success"}],
                        "operation": "other",
                        "affected_rows": cursor.rowcount,
                        "message": "Query executed successfully."
                    }), 200
                    
            except Exception as e:
                print(f"Error in local MySQL execution: {e}")
                try:
                    conn.rollback()
                    conn.close()
                except:
                    pass
                return jsonify({"error": f"Local MySQL error: {str(e)}"}), 500

    except Exception as e:
        print(f"Unexpected error in execute_query: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@db_routes.route('/import-cloud-database', methods=['POST'])
def import_cloud_database():
    data = request.get_json()
    user_id = data.get('user_id')
    db_name = data.get('db_name')
    db_type = data.get('db_type', 'cloud')
    host_url = data.get('host_url')
    username = data.get('username')
    password = data.get('password')

    if not all([user_id, db_name, host_url, username, password]):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        conn = pymysql.connect(
            host=host_url,
            user=username,
            password=password,
            database=db_name,
            cursorclass=pymysql.cursors.DictCursor
        )
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [row[list(row.keys())[0]] for row in cursor.fetchall()]
        schema = []
        for table in tables:
            cursor.execute(f"DESCRIBE `{table}`")
            columns = cursor.fetchall()
            column_info = []
            for col in columns:
                col_type = col['Type']
                column_info.append({
                    'name': col['Field'],
                    'type': col_type
                })
            schema.append({
                'table_name': table,
                'columns': column_info
            })
        conn.close()
    except Exception as e:
        return jsonify({'error': f'Failed to connect or fetch schema: {str(e)}'}), 500

    try:
        db_id = import_database(user_id, db_name, db_type, json.dumps(schema), username, password)
        insert_cloud_db_credentials(db_id, host_url, username, password)
        
        return jsonify({'message': 'Cloud database imported successfully.'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@db_routes.route('/import-mongodb', methods=['POST'])
def import_mongodb():
    data = request.get_json()
    user_id = data.get('user_id')
    db_name = data.get('db_name')
    username = data.get('username')
    password = data.get('password')

    if not all([user_id, db_name]):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        if username and password:
            connection_string = f'mongodb://{username}:{password}@localhost:27017/'
        else:
            connection_string = 'mongodb://localhost:27017/'
        
        client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        
        if db_name not in client.list_database_names():
            return jsonify({'error': f'MongoDB database "{db_name}" not found'}), 400
        
        db = client[db_name]
        collections = db.list_collection_names()
        
        if not collections:
            return jsonify({'error': f'No collections found in database "{db_name}"'}), 400
        
        schema = []
        for collection_name in collections:
            collection = db[collection_name]
            sample_doc = collection.find_one()
            
            if sample_doc:
                columns = []
                for field_name, field_value in sample_doc.items():
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
        
        client.close()
        
        schema_json = json.dumps(schema)
        import_database(user_id, db_name, 'mongodb', schema_json, username, password)
        
        return jsonify({
            'message': f'MongoDB database "{db_name}" imported successfully with {len(schema)} collections.',
            'schema': schema
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Failed to import MongoDB database: {str(e)}'}), 500

@db_routes.route('/convert-sql-to-mongodb', methods=['POST'])
def convert_sql_to_mongodb():
    try:
        data = request.get_json()
        sql_query = data.get('sqlQuery')
        db_name = data.get('dbName')
        schema = data.get('schema')

        if not sql_query or not db_name or not schema:
            return jsonify({"error": "Missing required data"}), 400

        # Simple local conversion without external API
        mongodb_query = convert_sql_to_mongodb_local(sql_query, schema)
        return jsonify({"mongodb": mongodb_query}), 200

    except Exception as e:
        return jsonify({"error": f"Error in /convert-sql-to-mongodb: {str(e)}"}), 500

def convert_sql_to_mongodb_local(sql_query, schema):
    """Simple SQL to MongoDB conversion"""
    query_lower = sql_query.lower().strip()
    
    # Basic patterns for SQL to MongoDB conversion
    if query_lower.startswith('select'):
        if 'from' in query_lower:
            # Extract table name
            from_index = query_lower.find('from')
            table_part = query_lower[from_index:].split()[1]
            table_name = table_part.strip(';')
            
            if 'where' in query_lower:
                return f"db.{table_name}.find({{}})"
            else:
                return f"db.{table_name}.find()"
        else:
            return "db.collection.find()"
    elif query_lower.startswith('insert'):
        if 'into' in query_lower:
            # Extract table name
            into_index = query_lower.find('into')
            table_part = query_lower[into_index:].split()[1]
            table_name = table_part.strip(';')
            return f"db.{table_name}.insertOne({{}})"
        else:
            return "db.collection.insertOne({})"
    elif query_lower.startswith('update'):
        if 'set' in query_lower:
            # Extract table name
            update_index = query_lower.find('update')
            table_part = query_lower[update_index:].split()[1]
            table_name = table_part.strip(';')
            return f"db.{table_name}.updateOne({{}}, {{$set: {{}}}})"
        else:
            return "db.collection.updateOne({}, {$set: {}})"
    elif query_lower.startswith('delete'):
        if 'from' in query_lower:
            # Extract table name
            from_index = query_lower.find('from')
            table_part = query_lower[from_index:].split()[1]
            table_name = table_part.strip(';')
            return f"db.{table_name}.deleteOne({{}})"
        else:
            return "db.collection.deleteOne({})"
    else:
        return "db.collection.find()"

@db_routes.route('/delete-database', methods=['POST'])
def delete_database_route():
    data = request.get_json()
    user_id = data.get('user_id')
    db_name = data.get('db_name')
    db_type = data.get('db_type')
    db_id = data.get('db_id')
    if not user_id or not db_name:
        return jsonify({'error': 'user_id and db_name are required'}), 400
    try:
        deleted = delete_database(user_id, db_name)
        if db_type == 'cloud' and db_id:
            delete_cloud_db_credentials(db_id)
        return jsonify({'message': 'Database deleted successfully.'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@db_routes.route('/test-mongodb', methods=['GET'])
def test_mongodb():
    """Test endpoint to check MongoDB connectivity and database registration"""
    try:
        db_name = request.args.get('db_name', 'ecommerce')
        print(f"Testing MongoDB for database: {db_name}")
        
        # Test 1: Check if database is registered
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM databases_info WHERE db_name = %s", (db_name,))
        db_info = cursor.fetchone()
        conn.close()
        
        if not db_info:
            return jsonify({"error": f"Database '{db_name}' not found in databases_info table"}), 404
        
        print(f"Database info: {db_info}")
        
        # Test 2: Check MongoDB connection
        try:
            client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            print("MongoDB connection successful")
            
            # Test 3: Check if database exists
            if db_name not in client.list_database_names():
                client.close()
                return jsonify({"error": f"MongoDB database '{db_name}' not found on server"}), 404
            
            db = client[db_name]
            collections = db.list_collection_names()
            print(f"Collections found: {collections}")
            
            # Test 4: Try a simple query
            if collections:
                collection_name = collections[0]
                collection = db[collection_name]
                sample = collection.find_one()
                print(f"Sample document from {collection_name}: {sample}")
            
            client.close()
            
            return jsonify({
                "status": "success",
                "database_info": db_info,
                "collections": collections,
                "message": "MongoDB connection and database access successful"
            }), 200
            
        except Exception as e:
            print(f"MongoDB connection error: {e}")
            return jsonify({"error": f"MongoDB connection failed: {str(e)}"}), 500
            
    except Exception as e:
        print(f"Test error: {e}")
        return jsonify({"error": f"Test failed: {str(e)}"}), 500
