# routes/db_routes.py
from flask import Blueprint, request, jsonify
from models.database_model import get_user_databases, import_database, get_database_schema, get_database_credentials
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
from models.cloud_db_credentials import insert_cloud_db_credentials, get_cloud_db_credentials
import json

db_routes = Blueprint('db_routes', __name__)

# Add debug logging for API key
print("\n=== Checking GROQ_API_KEY ===")
if GROQ_API_KEY:
    print("GROQ_API_KEY is set (length:", len(GROQ_API_KEY), "characters)")
else:
    print("GROQ_API_KEY is not set!")

@db_routes.route('/get-databases', methods=['GET'])
def get_databases():
    user_id = request.args.get('user_id')
    try:
        print("➡️ Fetching databases for user_id:", user_id)
        data = get_user_databases(user_id)
        print("Data fetched:", data)
        return jsonify(data), 200
    except Exception as e:
        print("ERROR in /get-databases:", e)
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@db_routes.route('/get-database-type', methods=['GET'])
def get_database_type():
    print("\n=== /get-database-type route called ===")
    db_name = request.args.get('db_name')
    print(f"Requested database name: {db_name}")
    
    if not db_name:
        print("ERROR: Database name is required")
        return jsonify({"error": "Database name is required"}), 400
    
    try:
        print(f"Connecting to database to fetch type for: {db_name}")
        conn = get_connection()
        cursor = conn.cursor()
        
        # Debug: Check if the database exists
        cursor.execute("SELECT COUNT(*) as count FROM databases_info WHERE db_name = %s", (db_name,))
        count_result = cursor.fetchone()
        print(f"🔍 Database count in databases_info: {count_result['count']}")
        
        # Get the database type
        cursor.execute("SELECT db_type FROM databases_info WHERE db_name = %s", (db_name,))
        result = cursor.fetchone()
        conn.close()
        
        print(f"🔍 Raw result from database: {result}")
        
        if not result:
            print(f"❌ ERROR: Database '{db_name}' not found in databases_info")
            return jsonify({"error": "Database not found"}), 404
        
        db_type = result['db_type']
        print(f"✅ Database type found: {db_type}")
        return jsonify({"db_type": db_type}), 200
        
    except Exception as e:
        print(f"❌ ERROR in /get-database-type: {e}")
        import traceback
        traceback.print_exc()
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
        print("❌ ERROR in /get-schema:", e)
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@db_routes.route('/import-database', methods=['POST'])
def import_db():
    data = request.get_json()
    user_id = data['user_id']
    db_name = data['db_name']
    db_type = data.get('db_type', 'local')
    username = data.get('username')  # New: username for local databases
    password = data.get('password')  # New: password for local databases

    try:
        # Get schema for the database
        schema = get_database_schema(db_name)
        schema_json = json.dumps(schema) if schema else None
        
        # Import database with credentials (encrypted)
        import_database(user_id, db_name, db_type, schema_json, username, password)
        return jsonify({"message": "Database imported successfully."}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@db_routes.route('/convert-to-sql', methods=['POST'])
def convert_to_sql():
    try:
        # Check if API key is set
        print("\n=== Checking GROQ_API_KEY ===")
        print("GROQ_API_KEY exists:", bool(GROQ_API_KEY))
        print("GROQ_API_KEY length:", len(GROQ_API_KEY) if GROQ_API_KEY else 0)
        
        if not GROQ_API_KEY:
            error_message = "GROQ_API_KEY is not set in environment variables"
            print("❌ ERROR:", error_message)
            return jsonify({"error": error_message}), 500

        print("\n=== Parsing Request Data ===")
        try:
            data = request.get_json()
            print("Request data type:", type(data))
            print("Request data:", data)
        except Exception as e:
            error_message = f"Error parsing request data: {str(e)}"
            print("❌ ERROR:", error_message)
            return jsonify({"error": error_message}), 400
        
        english_query = data.get('prompt')  # This will be the English query
        db_name = data.get('dbName')
        schema = data.get('schema')  # Get schema from frontend

        print("\n=== Extracted Data ===")
        print("English Query:", english_query)
        print("Database Name:", db_name)
        print("Schema type:", type(schema))
        print("Schema:", schema)

        if not english_query or not db_name or not schema:
            error_msg = f"Missing required data. English query: {bool(english_query)}, DB name: {bool(db_name)}, Schema: {bool(schema)}"
            print("❌ ERROR:", error_msg)
            return jsonify({"error": error_msg}), 400

        # Get database type from the database with enhanced error handling
        db_type = 'mysql'  # Default fallback
        try:
            print(f"\n=== Fetching Database Type for: {db_name} ===")
            conn = get_connection()
            cursor = conn.cursor()
            
            # Debug: Check if the database exists
            cursor.execute("SELECT COUNT(*) as count FROM databases_info WHERE db_name = %s", (db_name,))
            count_result = cursor.fetchone()
            print(f"🔍 Database count in databases_info: {count_result['count']}")
            
            # Get the database type
            cursor.execute("SELECT db_type FROM databases_info WHERE db_name = %s", (db_name,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                db_type = result['db_type']
                print(f"✅ Database type found: {db_type}")
            else:
                print(f"⚠️ Database '{db_name}' not found in databases_info, using default: {db_type}")
                
        except Exception as e:
            print(f"❌ Error getting database type: {e}")
            import traceback
            traceback.print_exc()
            print(f"⚠️ Using default database type: {db_type}")

        # Generate the prompt using appropriate prompt generator based on database type
        try:
            print(f"\n=== Generating Prompt for Database Type: {db_type} ===")
            print(f"🔍 Checking if db_type.lower() == 'mongodb': {db_type.lower() == 'mongodb'}")
            
            if db_type.lower() == 'mongodb':
                print("✅ Using MongoDB prompt generator")
                # Use the workspace-specific MongoDB prompt for better results
                prompt = generate_workspace_mongodb_prompt(english_query, schema)
                system_content = "You are a MongoDB expert that converts English queries to MongoDB. Provide only the MongoDB query without any explanations or markdown formatting. NEVER return SQL syntax."
                print("✅ MongoDB prompt generated successfully")
            else:
                print("✅ Using SQL prompt generator")
                prompt = generate_english_to_sql_prompt(english_query, schema)
                system_content = "You are a SQL expert that converts English queries to SQL. Provide only the SQL query without any explanations or markdown formatting."
                print("✅ SQL prompt generated successfully")
            
            print(f"🔍 Database type: {db_type}")
            print(f"🔍 System content: {system_content}")
            print(f"🔍 Prompt length: {len(prompt)} characters")
        except Exception as e:
            error_message = f"Error generating prompt: {str(e)}"
            print("❌ ERROR:", error_message)
            import traceback
            print("Prompt generation traceback:")
            traceback.print_exc()
            return jsonify({"error": error_message}), 500

        # Call Groq API for conversion
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        print("\n=== Making Groq API Request ===")
        print("Headers:", headers)
        request_body = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 100,
            "top_p": 1,
            "stream": False
        }
        print("Request body:", request_body)
        
        try:
            print("\n=== Sending Request to Groq API ===")
            response = requests.post('https://api.groq.com/openai/v1/chat/completions',
                headers=headers,
                json=request_body,
                timeout=30  # Add timeout
            )
            print("Request sent successfully")
        except requests.exceptions.RequestException as e:
            error_message = f"Error making request to Groq API: {str(e)}"
            print("❌ ERROR:", error_message)
            import traceback
            print("Request error traceback:")
            traceback.print_exc()
            return jsonify({"error": error_message}), 500

        print("\n=== Groq API Response ===")
        print("Response status code:", response.status_code)
        print("Response headers:", dict(response.headers))
        print("Response body:", response.text)

        if response.status_code != 200:
            error_message = f"Failed to get response from Groq API. Status code: {response.status_code}, Response: {response.text}"
            print("❌ ERROR:", error_message)
            return jsonify({"error": error_message}), 500

        try:
            # Extract the query from the response
            response_data = response.json()
            print("\n=== Parsing Response Data ===")
            print("Response data:", response_data)
            
            if 'choices' not in response_data or not response_data['choices']:
                error_message = "Invalid response format from Groq API"
                print("❌ ERROR:", error_message)
                return jsonify({"error": error_message}), 500

            generated_query = response_data['choices'][0]['message']['content'].strip()
            print("\n=== Generated Query ===")
            print(generated_query)
            
            # Return appropriate response based on database type
            if db_type.lower() == 'mongodb':
                print("✅ Returning MongoDB response")
                return jsonify({"mongodb": generated_query}), 200
            else:
                print("✅ Returning SQL response")
                return jsonify({"sql": generated_query}), 200
                
        except (KeyError, IndexError) as e:
            error_message = f"Error parsing Groq API response: {str(e)}"
            print("❌ ERROR:", error_message)
            import traceback
            print("Response parsing traceback:")
            traceback.print_exc()
            return jsonify({"error": error_message}), 500

    except Exception as e:
        error_message = f"Error in /convert-to-sql: {str(e)}"
        print("\n❌ ERROR:", error_message)
        import traceback
        print("Main error traceback:")
        traceback.print_exc()
        return jsonify({"error": error_message}), 500

@db_routes.route('/convert-to-english', methods=['POST'])
def convert_to_english():
    print("\n=== Starting /convert-to-english route ===")
    try:
        # Check if API key is set
        print("\n=== Checking GROQ_API_KEY ===")
        print("GROQ_API_KEY exists:", bool(GROQ_API_KEY))
        print("GROQ_API_KEY length:", len(GROQ_API_KEY) if GROQ_API_KEY else 0)
        
        if not GROQ_API_KEY:
            error_message = "GROQ_API_KEY is not set in environment variables"
            print("❌ ERROR:", error_message)
            return jsonify({"error": error_message}), 500

        print("\n=== Parsing Request Data ===")
        try:
            data = request.get_json()
            print("Request data type:", type(data))
            print("Request data:", data)
        except Exception as e:
            error_message = f"Error parsing request data: {str(e)}"
            print("❌ ERROR:", error_message)
            return jsonify({"error": error_message}), 400
            
        query = data.get('prompt')
        db_name = data.get('dbName')
        schema = data.get('schema')
        
        print("\n=== Extracted Data ===")
        print("Query:", query)
        print("Database Name:", db_name)
        print("Schema type:", type(schema))
        print("Schema:", schema)
        
        if not query or not db_name or not schema:
            error_msg = f"Missing required data. Query: {bool(query)}, DB name: {bool(db_name)}, Schema: {bool(schema)}"
            print("❌ ERROR:", error_msg)
            return jsonify({"error": error_msg}), 400

        # Get database type from the database
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT db_type FROM databases_info WHERE db_name = %s", (db_name,))
            result = cursor.fetchone()
            db_type = result['db_type'] if result else 'mysql'
            conn.close()
            print(f"Database type detected: {db_type}")
        except Exception as e:
            print(f"Error getting database type: {e}")
            db_type = 'mysql'  # Default to MySQL if error
            
        # Generate the prompt using appropriate prompt generator based on database type
        try:
            print("\n=== Generating Prompt ===")
            if db_type.lower() == 'mongodb':
                prompt = generate_mongodb_to_english_prompt(query, schema)
                system_content = "You are a MongoDB expert that explains MongoDB queries in plain English. Provide a clear and concise explanation of what the MongoDB query does."
            else:
                prompt = generate_sql_to_english_prompt(query, schema)
                system_content = "You are a SQL expert that explains SQL queries in plain English. Provide a clear and concise explanation of what the SQL query does."
            
            print("Generated prompt:", prompt)
            print("Database type:", db_type)
        except Exception as e:
            error_message = f"Error generating prompt: {str(e)}"
            print("❌ ERROR:", error_message)
            import traceback
            print("Prompt generation traceback:")
            traceback.print_exc()
            return jsonify({"error": error_message}), 500
        
        # Call Groq API for conversion
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        print("\n=== Making Groq API Request ===")
        print("Headers:", headers)
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
        print("Request body:", request_body)
        
        try:
            print("\n=== Sending Request to Groq API ===")
            response = requests.post('https://api.groq.com/openai/v1/chat/completions',
                headers=headers,
                json=request_body,
                timeout=30  # Add timeout
            )
            print("Request sent successfully")
        except requests.exceptions.RequestException as e:
            error_message = f"Error making request to Groq API: {str(e)}"
            print("❌ ERROR:", error_message)
            import traceback
            print("Request error traceback:")
            traceback.print_exc()
            return jsonify({"error": error_message}), 500
        
        print("\n=== Groq API Response ===")
        print("Response status code:", response.status_code)
        print("Response headers:", dict(response.headers))
        print("Response body:", response.text)

        if response.status_code != 200:
            error_message = f"Failed to get response from Groq API. Status code: {response.status_code}, Response: {response.text}"
            print("❌ ERROR:", error_message)
            return jsonify({"error": error_message}), 500

        try:
            # Extract the English description from the response
            response_data = response.json()
            print("\n=== Parsing Response Data ===")
            print("Response data:", response_data)
            
            if 'choices' not in response_data or not response_data['choices']:
                error_message = "Invalid response format from Groq API"
                print("❌ ERROR:", error_message)
                return jsonify({"error": error_message}), 500

            english_description = response_data['choices'][0]['message']['content'].strip()
            print("\n=== Generated English Description ===")
            print(english_description)
            
            return jsonify({"english": english_description}), 200
        except (KeyError, IndexError) as e:
            error_message = f"Error parsing Groq API response: {str(e)}"
            print("❌ ERROR:", error_message)
            import traceback
            print("Response parsing traceback:")
            traceback.print_exc()
            return jsonify({"error": error_message}), 500
            
    except Exception as e:
        error_message = f"Error in /convert-to-english: {str(e)}"
        print("\n❌ ERROR:", error_message)
        import traceback
        print("Main error traceback:")
        traceback.print_exc()
        return jsonify({"error": error_message}), 500

@db_routes.route('/execute-query', methods=['POST'])
def execute_query():
    print("\n=== /execute-query route called ===")
    try:
        data = request.get_json()
        print(f"🔍 Request data: {data}")
        
        db_name = data.get('dbName')
        query = data.get('query')
        user_id = data.get('user_id')  # Get user_id from request

        print(f"🔍 Database name: {db_name}")
        print(f"🔍 Query: {query}")
        print(f"🔍 User ID: {user_id}")

        if not db_name or not query:
            error_msg = "Missing database name or query"
            print(f"❌ ERROR: {error_msg}")
            return jsonify({"error": error_msg}), 400

        # Fetch db_type with user_id to ensure proper access
        print(f"🔍 Fetching database info for: {db_name} and user_id: {user_id}")
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        if user_id:
            # Look up database with user_id to ensure access control
            cursor.execute("SELECT db_id, db_type FROM databases_info WHERE db_name = %s AND user_id = %s", (db_name, user_id))
        else:
            # Fallback to just db_name if user_id not provided
            cursor.execute("SELECT db_id, db_type FROM databases_info WHERE db_name = %s", (db_name,))
            
        db_info = cursor.fetchone()
        conn.close()

        if not db_info:
            error_msg = f"Database '{db_name}' not found or access denied for user_id: {user_id}"
            print(f"❌ ERROR: {error_msg}")
            return jsonify({"error": error_msg}), 400

        print(f"🔍 Database info: {db_info}")
        print(f"🔍 Database ID: {db_info['db_id']}")
        print(f"🔍 Database type: {db_info['db_type']}")

        if db_info['db_type'] == 'mongodb':
            print("🔍 Processing MongoDB database")
            # Handle MongoDB queries
            try:
                from pymongo import MongoClient
                
                # Get stored credentials for MongoDB
                creds = get_database_credentials(db_info['db_id'])
                
                # Build connection string based on stored credentials
                if creds and creds.get('username') and creds.get('password'):
                    # Use authentication
                    connection_string = f'mongodb://{creds["username"]}:{creds["password"]}@localhost:27017/'
                    print(f"🔍 Connecting to MongoDB with authentication: {creds['username']}")
                else:
                    # No authentication
                    connection_string = 'mongodb://localhost:27017/'
                    print("🔍 Connecting to MongoDB without authentication")
                
                # Connect to MongoDB
                client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
                
                # Test connection
                client.admin.command('ping')
                print("✅ MongoDB connection successful")
                
                db = client[db_name]
                
                # Parse and execute MongoDB query
                if query.strip().lower().startswith('db.'):
                    # Extract collection name and operation from MongoDB syntax
                    parts = query.strip().split('.')
                    if len(parts) >= 2:
                        collection_name = parts[1]
                        collection = db[collection_name]
                        
                        # Handle different MongoDB operations
                        if 'find(' in query:
                            # Handle find operations
                            start_idx = query.find('find(') + 5
                            end_idx = query.rfind(')')
                            if end_idx > start_idx:
                                query_params = query[start_idx:end_idx].strip()
                                
                                if query_params == '':
                                    results = list(collection.find())
                                else:
                                    try:
                                        import json
                                        params = json.loads(query_params)
                                        results = list(collection.find(params))
                                    except json.JSONDecodeError:
                                        results = list(collection.find(eval(query_params)))
                            else:
                                results = list(collection.find())
                            
                            # Convert MongoDB documents to list of dictionaries
                            rows = []
                            columns = []
                            
                            if results:
                                # Get all unique column names from all documents to ensure consistent order
                                all_columns = set()
                                for doc in results:
                                    all_columns.update(doc.keys())
                                
                                # Convert to list and sort for consistent order
                                columns = sorted(list(all_columns))
                                
                                # Debug: Log column order for MongoDB
                                print(f"🔍 MongoDB column order: {columns}")
                                
                                # Process each document to ensure all columns are present
                                for doc in results:
                                    # Create a new document with all columns in the same order
                                    ordered_doc = {}
                                    for col in columns:
                                        if col in doc:
                                            # Convert ObjectId to string for JSON serialization
                                            if col == '_id':
                                                ordered_doc[col] = str(doc[col])
                                            else:
                                                ordered_doc[col] = doc[col]
                                        else:
                                            ordered_doc[col] = None
                                    rows.append(ordered_doc)
                            
                            client.close()
                            return jsonify({
                                "columns": columns,
                                "rows": rows,
                                "operation": "find",
                                "affected_rows": len(rows)
                            }), 200
                            
                        elif 'insert(' in query or 'insertOne(' in query:
                            # Handle insert operations
                            start_idx = query.find('(') + 1
                            end_idx = query.rfind(')')
                            if end_idx > start_idx:
                                doc_data = query[start_idx:end_idx].strip()
                                try:
                                    import json
                                    document = json.loads(doc_data)
                                    result = collection.insert_one(document)
                                    client.close()
                                    return jsonify({
                                        "columns": ["inserted_id"],
                                        "rows": [{"inserted_id": str(result.inserted_id)}],
                                        "operation": "insert",
                                        "affected_rows": 1,
                                        "message": f"Document inserted successfully with ID: {result.inserted_id}"
                                    }), 200
                                except json.JSONDecodeError:
                                    return jsonify({"error": "Invalid JSON format for insert operation"}), 400
                            else:
                                return jsonify({"error": "Invalid insert operation format"}), 400
                                
                        elif 'update(' in query or 'updateOne(' in query or 'updateMany(' in query:
                            # Handle update operations
                            start_idx = query.find('(') + 1
                            end_idx = query.rfind(')')
                            if end_idx > start_idx:
                                update_params = query[start_idx:end_idx].strip()
                                try:
                                    import json
                                    
                                    # Find the first two JSON objects
                                    brace_count = 0
                                    filter_end = -1
                                    for i, char in enumerate(update_params):
                                        if char == '{':
                                            brace_count += 1
                                        elif char == '}':
                                            brace_count -= 1
                                            if brace_count == 0 and filter_end == -1:
                                                filter_end = i
                                                break
                                    
                                    if filter_end != -1:
                                        filter_str = update_params[:filter_end+1]
                                        update_str = update_params[filter_end+1:].strip()
                                        if update_str.startswith(','):
                                            update_str = update_str[1:].strip()
                                        
                                        filter_doc = json.loads(filter_str)
                                        update_doc = json.loads(update_str)
                                        
                                        if 'updateOne' in query:
                                            result = collection.update_one(filter_doc, update_doc)
                                        else:
                                            result = collection.update_many(filter_doc, update_doc)
                                        
                                        client.close()
                                        return jsonify({
                                            "columns": ["matched_count", "modified_count"],
                                            "rows": [{"matched_count": result.matched_count, "modified_count": result.modified_count}],
                                            "operation": "update",
                                            "affected_rows": result.modified_count,
                                            "message": f"Updated {result.modified_count} document(s) out of {result.matched_count} matched"
                                        }), 200
                                except Exception as e:
                                    return jsonify({"error": f"Error parsing update operation: {str(e)}"}), 400
                            else:
                                return jsonify({"error": "Invalid update operation format"}), 400
                                
                        elif 'delete(' in query or 'deleteOne(' in query or 'deleteMany(' in query:
                            # Handle delete operations
                            start_idx = query.find('(') + 1
                            end_idx = query.rfind(')')
                            if end_idx > start_idx:
                                filter_str = query[start_idx:end_idx].strip()
                                try:
                                    filter_doc = json.loads(filter_str)
                                    
                                    if 'deleteOne' in query:
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
                                except json.JSONDecodeError:
                                    return jsonify({"error": "Invalid JSON format for delete operation"}), 400
                            else:
                                return jsonify({"error": "Invalid delete operation format"}), 400
                        else:
                            return jsonify({"error": "Unsupported MongoDB operation. Supported: find, insert, update, delete"}), 400
                    else:
                        return jsonify({"error": "Invalid MongoDB query format. Use: db.collection.operation()"}), 400
                else:
                    return jsonify({"error": "MongoDB queries must start with 'db.'"}), 400
                    
            except Exception as e:
                error_msg = f"MongoDB query error: {str(e)}"
                print(f"❌ ERROR: {error_msg}")
                return jsonify({"error": error_msg}), 500
                
        elif db_info['db_type'] == 'cloud':
            print(f"🔍 Processing CLOUD database: {db_name}")
            print(f"🔍 Database ID: {db_info['db_id']}")
            
            # Get credentials from cloud_db_credentials table (includes host_url)
            try:
                print(f"🔍 Calling get_cloud_db_credentials for db_id: {db_info['db_id']}")
                creds = get_cloud_db_credentials(db_info['db_id'])
                print(f"🔍 Cloud credentials fetched: {creds is not None}")
                print(f"🔍 Credentials type: {type(creds)}")
                
                if not creds:
                    error_msg = f"Cloud DB credentials not found for database ID: {db_info['db_id']}"
                    print(f"❌ ERROR: {error_msg}")
                    return jsonify({"error": error_msg}), 500
                
                print(f"🔍 Credentials keys: {list(creds.keys()) if creds else 'None'}")
                print(f"🔍 Connecting to cloud database: {creds.get('host_url', 'NOT_FOUND')}")
                print(f"🔍 Username: {creds.get('username', 'NOT_FOUND')}")
                print(f"🔍 Database name: {db_name}")
                
                # Connect to cloud database with timeout and error handling
                conn = pymysql.connect(
                    host=creds['host_url'],
                    user=creds['username'],
                    password=creds['password'],
                    database=db_name,
                    cursorclass=pymysql.cursors.DictCursor,
                    autocommit=False,  # Disable autocommit for transaction control
                    connect_timeout=30,  # Add connection timeout
                    read_timeout=30,     # Add read timeout
                    write_timeout=30     # Add write timeout
                )
                print("✅ Cloud database connection successful")
                
            except Exception as e:
                error_msg = f"Failed to connect to cloud database: {str(e)}"
                print(f"❌ ERROR: {error_msg}")
                import traceback
                traceback.print_exc()
                return jsonify({"error": error_msg}), 500
        else:
            # Local MySQL - use stored credentials if available
            print(f"🔍 Connecting to local MySQL database: {db_name}")
            
            try:
                # Try to get stored credentials first
                creds = get_database_credentials(db_info['db_id'])
                if creds:
                    print(f"🔍 Using stored credentials for local database")
                    conn = pymysql.connect(
                        host="localhost",
                        user=creds['username'],
                        password=creds['password'],
                        database=db_name,
                        cursorclass=pymysql.cursors.DictCursor,
                        autocommit=False
                    )
                else:
                    # Fallback to default credentials
                    print(f"🔍 Using default credentials for local database")
                    conn = pymysql.connect(
                        host="localhost",
                        user="root",
                        password="Rakshita2305",
                        database=db_name,
                        cursorclass=pymysql.cursors.DictCursor,
                        autocommit=False
                    )
            except Exception as e:
                error_msg = f"Failed to connect to local database: {str(e)}"
                print(f"❌ ERROR: {error_msg}")
                return jsonify({"error": error_msg}), 500
        
        # For MySQL databases (both local and cloud)
        cursor = conn.cursor()
        
        try:
            print(f"🔍 Executing query: {query}")
            print(f"🔍 Database: {db_name}")
            print(f"🔍 Database type: {db_info['db_type']}")
            
            # Execute the query
            cursor.execute(query)
            
            # Determine query type and handle accordingly
            query_lower = query.strip().lower()
            print(f"🔍 Query type detected: {query_lower[:20]}...")
            
            if query_lower.startswith('select'):
                # SELECT query - fetch results
                print("🔍 Processing SELECT query")
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = cursor.fetchall()
                
                # Debug: Log column order for SELECT queries
                print(f"🔍 Column order for SELECT: {columns}")
                if rows and len(rows) > 0:
                    print(f"🔍 First row keys: {list(rows[0].keys())}")
                
                conn.commit()  # Commit any pending transaction
                conn.close()
                
                print(f"✅ SELECT successful - {len(rows)} rows returned")
                return jsonify({
                    "columns": columns,
                    "rows": rows,
                    "operation": "select",
                    "affected_rows": len(rows)
                }), 200
                
            elif any(query_lower.startswith(op) for op in ['insert', 'update', 'delete']):
                # INSERT, UPDATE, DELETE query - commit and return affected rows
                print("🔍 Processing INSERT/UPDATE/DELETE query")
                affected_rows = cursor.rowcount
                print(f"🔍 Affected rows: {affected_rows}")
                
                # IMPORTANT: Commit the transaction to save changes
                conn.commit()
                print(f"✅ Transaction committed successfully")
                conn.close()
                
                operation = "insert" if query_lower.startswith('insert') else "update" if query_lower.startswith('update') else "delete"
                
                print(f"✅ {operation.upper()} successful - {affected_rows} rows affected")
                return jsonify({
                    "columns": ["affected_rows"],
                    "rows": [{"affected_rows": affected_rows}],
                    "operation": operation,
                    "affected_rows": affected_rows,
                    "message": f"{operation.capitalize()} operation completed. {affected_rows} row(s) affected."
                }), 200
                
            elif any(query_lower.startswith(op) for op in ['create', 'alter', 'drop', 'truncate']):
                # DDL operations - commit and return success
                print("🔍 Processing DDL query")
                conn.commit()
                conn.close()
                
                operation = "create" if query_lower.startswith('create') else "alter" if query_lower.startswith('alter') else "drop" if query_lower.startswith('drop') else "truncate"
                
                print(f"✅ {operation.upper()} successful")
                return jsonify({
                    "columns": ["status"],
                    "rows": [{"status": "success"}],
                    "operation": operation,
                    "affected_rows": 0,
                    "message": f"{operation.capitalize()} operation completed successfully."
                }), 200
                
            else:
                # Other operations (like SHOW, DESCRIBE, etc.)
                print("🔍 Processing other query type")
                try:
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    rows = cursor.fetchall()
                    conn.commit()
                    conn.close()
                    
                    print(f"✅ Other query successful - {len(rows)} rows returned")
                    return jsonify({
                        "columns": columns,
                        "rows": rows,
                        "operation": "other",
                        "affected_rows": len(rows)
                    }), 200
                except Exception as fetch_error:
                    print(f"⚠️ fetchall failed, treating as non-SELECT query: {fetch_error}")
                    # If fetchall fails, it might be a non-SELECT query
                    conn.commit()
                    conn.close()
                    
                    print("✅ Non-SELECT query completed successfully")
                    return jsonify({
                        "columns": ["status"],
                        "rows": [{"status": "success"}],
                        "operation": "other",
                        "affected_rows": 0,
                        "message": "Query executed successfully."
                    }), 200
                    
        except Exception as e:
            # Enhanced error handling for cloud databases
            print(f"❌ Query execution error: {str(e)}")
            print(f"❌ Database type: {db_info['db_type']}")
            print(f"❌ Database name: {db_name}")
            
            # Provide more specific error messages for common cloud database issues
            error_message = str(e)
            if "Access denied" in error_message:
                error_message = "Access denied. Please check your cloud database credentials."
            elif "Connection refused" in error_message:
                error_message = "Connection refused. Please check your cloud database host URL and ensure it's accessible."
            elif "timeout" in error_message.lower():
                error_message = "Connection timeout. Please check your cloud database connection settings."
            elif "Unknown database" in error_message:
                error_message = f"Database '{db_name}' not found on the cloud server."
            
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            
            return jsonify({"error": error_message}), 500

    except Exception as e:
        print("❌ ERROR in /execute-query:", e)
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

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
        # Connect to the cloud MySQL database
        conn = pymysql.connect(
            host=host_url,
            user=username,
            password=password,
            database=db_name,
            cursorclass=pymysql.cursors.DictCursor
        )
        cursor = conn.cursor()
        # Fetch schema: get all tables and columns
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
        # Store in databases_info with encrypted credentials (for general access)
        db_id = import_database(user_id, db_name, db_type, json.dumps(schema), username, password)
        
        # Store in cloud_db_credentials with host_url (for cloud-specific access)
        insert_cloud_db_credentials(db_id, host_url, username, password)
        
        return jsonify({'message': 'Cloud database imported successfully.'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@db_routes.route('/import-mongodb', methods=['POST'])
def import_mongodb():
    data = request.get_json()
    user_id = data.get('user_id')
    db_name = data.get('db_name')
    username = data.get('username')  # Optional
    password = data.get('password')  # Optional

    if not all([user_id, db_name]):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        from pymongo import MongoClient
        
        # Build connection string based on credentials
        if username and password:
            # Use authentication
            connection_string = f'mongodb://{username}:{password}@localhost:27017/'
            print(f"🔍 Connecting to MongoDB with authentication: {username}")
        else:
            # No authentication
            connection_string = 'mongodb://localhost:27017/'
            print("🔍 Connecting to MongoDB without authentication")
        
        # Connect to MongoDB
        client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
        
        # Test connection
        client.admin.command('ping')
        print("✅ MongoDB connection successful")
        
        # Check if database exists
        if db_name not in client.list_database_names():
            return jsonify({'error': f'MongoDB database "{db_name}" not found'}), 400
        
        db = client[db_name]
        collections = db.list_collection_names()
        
        if not collections:
            return jsonify({'error': f'No collections found in database "{db_name}"'}), 400
        
        print(f"✅ Found {len(collections)} collections in database '{db_name}'")
        
        # Build schema
        schema = []
        for collection_name in collections:
            collection = db[collection_name]
            
            # Get sample documents to determine fields
            sample_docs = list(collection.find().limit(10))
            
            if sample_docs:
                # Get all unique fields from sample documents
                fields = set()
                for doc in sample_docs:
                    fields.update(doc.keys())
                
                # Convert to schema format
                columns = []
                for field in sorted(fields):
                    # Determine field type based on sample data
                    field_type = "string"  # default
                    for doc in sample_docs:
                        if field in doc:
                            if isinstance(doc[field], int):
                                field_type = "int"
                            elif isinstance(doc[field], float):
                                field_type = "float"
                            elif isinstance(doc[field], bool):
                                field_type = "boolean"
                            elif isinstance(doc[field], dict):
                                field_type = "object"
                            elif isinstance(doc[field], list):
                                field_type = "array"
                            break
                    
                    columns.append({
                        'name': field,
                        'type': field_type
                    })
                
                schema.append({
                    'table_name': collection_name,
                    'columns': columns
                })
        
        client.close()
        
        # Store in databases_info with encrypted credentials (only if provided)
        db_id = import_database(user_id, db_name, 'mongodb', json.dumps(schema), username, password)
        
        return jsonify({
            'message': f'MongoDB database "{db_name}" imported successfully with {len(schema)} collections.',
            'schema': schema
        }), 201
        
    except Exception as e:
        print(f"❌ MongoDB import error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to import MongoDB database: {str(e)}'}), 500

@db_routes.route('/convert-sql-to-mongodb', methods=['POST'])
def convert_sql_to_mongodb():
    try:
        # Check if API key is set
        print("\n=== Checking GROQ_API_KEY ===")
        print("GROQ_API_KEY exists:", bool(GROQ_API_KEY))
        print("GROQ_API_KEY length:", len(GROQ_API_KEY) if GROQ_API_KEY else 0)
        
        if not GROQ_API_KEY:
            error_message = "GROQ_API_KEY is not set in environment variables"
            print("❌ ERROR:", error_message)
            return jsonify({"error": error_message}), 500

        print("\n=== Parsing Request Data ===")
        try:
            data = request.get_json()
            print("Request data type:", type(data))
            print("Request data:", data)
        except Exception as e:
            error_message = f"Error parsing request data: {str(e)}"
            print("❌ ERROR:", error_message)
            return jsonify({"error": error_message}), 400
        
        sql_query = data.get('sqlQuery')
        db_name = data.get('dbName')
        schema = data.get('schema')

        print("\n=== Extracted Data ===")
        print("SQL Query:", sql_query)
        print("Database Name:", db_name)
        print("Schema type:", type(schema))
        print("Schema:", schema)

        if not sql_query or not db_name or not schema:
            error_msg = f"Missing required data. SQL query: {bool(sql_query)}, DB name: {bool(db_name)}, Schema: {bool(schema)}"
            print("❌ ERROR:", error_msg)
            return jsonify({"error": error_msg}), 400

        # Generate the prompt for SQL to MongoDB conversion
        try:
            print("\n=== Generating SQL to MongoDB Prompt ===")
            
            # Format schema text for MongoDB
            schema_text = ""
            for collection in schema:
                schema_text += f"Collection: {collection['table_name']}\n"
                schema_text += "Fields:\n"
                for field in collection['columns']:
                    schema_text += f"- {field['name']} ({field['type']})\n"
                schema_text += "\n"
            
            prompt = f"""You are a MongoDB expert. Convert the following SQL query into a valid MongoDB query.
IMPORTANT: You MUST return ONLY MongoDB syntax, NEVER SQL syntax.

The query should use proper MongoDB syntax and use the provided database schema.
Return ONLY the MongoDB query without any explanations or additional text. Please provide the query with lowest complexity(easiest).

IMPORTANT: Prefix your MongoDB query with "// MongoDB" comment.

CRITICAL RULES:
- NEVER use SQL keywords like SELECT, FROM, WHERE, INSERT INTO, UPDATE, DELETE FROM
- ALWAYS use MongoDB syntax: db.collection.operation()
- Use MongoDB operators like $gt, $lt, $gte, $lte, $eq, $ne, $in, $nin
- Use MongoDB methods: find(), findOne(), insertOne(), insertMany(), updateOne(), updateMany(), deleteOne(), deleteMany()

SQL to MongoDB Conversion Examples:
- SELECT * FROM users → // MongoDB
  db.users.find()
- SELECT * FROM users WHERE age > 25 → // MongoDB
  db.users.find({{"age": {{"$gt": 25}}}})
- SELECT * FROM users WHERE name = 'John' → // MongoDB
  db.users.find({{"name": "John"}})
- INSERT INTO users (name, age) VALUES ('John', 30) → // MongoDB
  db.users.insertOne({{"name": "John", "age": 30}})
- UPDATE users SET age = 31 WHERE name = 'John' → // MongoDB
  db.users.updateOne({{"name": "John"}}, {{"$set": {{"age": 31}}}})
- DELETE FROM users WHERE name = 'John' → // MongoDB
  db.users.deleteOne({{"name": "John"}})

SQL Query to Convert: {sql_query}

Database Schema:
{schema_text}

MongoDB Query:"""
            
            print("Generated prompt:", prompt)
            
        except Exception as e:
            error_message = f"Error generating prompt: {str(e)}"
            print("❌ ERROR:", error_message)
            import traceback
            print("Prompt generation traceback:")
            traceback.print_exc()
            return jsonify({"error": error_message}), 500

        # Call Groq API for conversion
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        print("\n=== Making Groq API Request ===")
        print("Headers:", headers)
        request_body = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [
                {"role": "system", "content": "You are a MongoDB expert that converts SQL queries to MongoDB. Provide only the MongoDB query without any explanations or markdown formatting. NEVER return SQL syntax."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 100,
            "top_p": 1,
            "stream": False
        }
        print("Request body:", request_body)
        
        try:
            print("\n=== Sending Request to Groq API ===")
            response = requests.post('https://api.groq.com/openai/v1/chat/completions',
                headers=headers,
                json=request_body,
                timeout=30
            )
            print("Request sent successfully")
        except requests.exceptions.RequestException as e:
            error_message = f"Error making request to Groq API: {str(e)}"
            print("❌ ERROR:", error_message)
            import traceback
            print("Request error traceback:")
            traceback.print_exc()
            return jsonify({"error": error_message}), 500

        print("\n=== Groq API Response ===")
        print("Response status code:", response.status_code)
        print("Response headers:", dict(response.headers))
        print("Response body:", response.text)

        if response.status_code != 200:
            error_message = f"Failed to get response from Groq API. Status code: {response.status_code}, Response: {response.text}"
            print("❌ ERROR:", error_message)
            return jsonify({"error": error_message}), 500

        try:
            # Extract the MongoDB query from the response
            response_data = response.json()
            print("\n=== Parsing Response Data ===")
            print("Response data:", response_data)
            
            if 'choices' not in response_data or not response_data['choices']:
                error_message = "Invalid response format from Groq API"
                print("❌ ERROR:", error_message)
                return jsonify({"error": error_message}), 500

            mongodb_query = response_data['choices'][0]['message']['content'].strip()
            print("\n=== Generated MongoDB Query ===")
            print(mongodb_query)
            
            return jsonify({"mongodb": mongodb_query}), 200
                
        except (KeyError, IndexError) as e:
            error_message = f"Error parsing Groq API response: {str(e)}"
            print("❌ ERROR:", error_message)
            import traceback
            print("Response parsing traceback:")
            traceback.print_exc()
            return jsonify({"error": error_message}), 500

    except Exception as e:
        error_message = f"Error in /convert-sql-to-mongodb: {str(e)}"
        print("\n❌ ERROR:", error_message)
        import traceback
        print("Main error traceback:")
        traceback.print_exc()
        return jsonify({"error": error_message}), 500
