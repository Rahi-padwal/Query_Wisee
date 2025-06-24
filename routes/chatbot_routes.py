from flask import Blueprint, request, jsonify
import requests
import json
from datetime import datetime
from db_config import get_connection
from config import GROQ_API_KEY
from pymongo import MongoClient
import pymysql
from models.database_model import get_database_schema
from utils.prompt_generator import generate_mongodb_learning_prompt

chatbot_routes = Blueprint('chatbot_routes', __name__)

@chatbot_routes.route('/test-chatbot', methods=['GET'])
def test_chatbot():
    return jsonify({"message": "Chatbot routes are working!"}), 200

@chatbot_routes.route('/test-groq', methods=['GET'])
def test_groq():
    try:
        if not GROQ_API_KEY:
            return jsonify({"error": "GROQ_API_KEY is not set"}), 500
        
        # Test a simple request to Groq
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        request_body = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "temperature": 0.1,
            "max_tokens": 10,
            "top_p": 1,
            "stream": False
        }
        
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers=headers,
            json=request_body,
            timeout=10
        )
        
        if response.status_code == 200:
            return jsonify({"message": "GROQ API is working!", "status": "success"}), 200
        else:
            return jsonify({"error": f"GROQ API error: {response.status_code} - {response.text}"}), 500
            
    except Exception as e:
        return jsonify({"error": f"GROQ API test failed: {str(e)}"}), 500

@chatbot_routes.route('/send-message', methods=['POST', 'OPTIONS'])
def send_message():
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        print("\n=== Starting Chatbot Message Processing ===")
        print("Request method:", request.method)
        print("Request headers:", dict(request.headers))
        
        # Check if API key is set
        if not GROQ_API_KEY:
            error_message = "GROQ_API_KEY is not set in environment variables"
            print("❌ ERROR:", error_message)
            return jsonify({"error": error_message}), 500

        # Parse request data
        try:
            data = request.get_json()
            print("Request data received:", data)
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            return jsonify({"error": "Invalid JSON data"}), 400

        user_id = data.get('user_id')
        db_name = data.get('db_name')
        message = data.get('message')
        chat_history = data.get('chat_history', [])

        print(f"User ID: {user_id}")
        print(f"Database: {db_name}")
        print(f"Message: {message}")
        print(f"Chat History Length: {len(chat_history)}")

        if not user_id or not db_name or not message:
            error_msg = f"Missing required data. User ID: {bool(user_id)}, DB name: {bool(db_name)}, Message: {bool(message)}"
            print(f"❌ ERROR: {error_msg}")
            return jsonify({"error": error_msg}), 400

        # Get database type and schema using the shared utility
        try:
            schema = get_database_schema(db_name)
            # Also get db_type for prompt context
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT db_type FROM databases_info WHERE db_name = %s", (db_name,))
            result = cursor.fetchone()
            db_type = result['db_type'] if result else 'mysql'
            conn.close()
            print(f"Database type detected: {db_type}")
            print(f"Schema loaded successfully, {len(schema)} tables/collections")
        except Exception as e:
            print(f"Error getting schema: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"Error retrieving database schema: {str(e)}"}), 500

        # Generate chatbot response
        try:
            print("Generating chatbot response...")
            response_text = generate_chatbot_response(message, db_type, schema, chat_history)
            print("Response generated successfully")
            
            print("Saving chat message...")
            save_chat_message(user_id, db_name, message, response_text, db_type)
            print("Chat message saved")
            
            return jsonify({
                "response": response_text,
                "timestamp": datetime.now().isoformat()
            }), 200
        except Exception as e:
            error_message = str(e)
            print(f"Error generating response: {error_message}")
            import traceback
            traceback.print_exc()
            save_chat_message(user_id, db_name, message, error_message, db_type, is_error=True)
            return jsonify({"error": error_message}), 500

    except Exception as e:
        print(f"❌ ERROR in /send-message: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@chatbot_routes.route('/get-chat-history', methods=['GET'])
def get_chat_history():
    try:
        user_id = request.args.get('user_id')
        db_name = request.args.get('db_name')
        
        if not user_id or not db_name:
            return jsonify({"error": "Missing user_id or db_name"}), 400
            
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Check if chat_history table exists
            cursor.execute("""
                SELECT COUNT(*) as table_exists 
                FROM information_schema.tables 
                WHERE table_schema = 'ai_sql_assistant' 
                AND table_name = 'chat_history'
            """)
            table_exists = cursor.fetchone()['table_exists'] > 0
            
            if not table_exists:
                print("chat_history table does not exist, returning empty history")
                conn.close()
                return jsonify({"chat_history": []}), 200
            
            cursor.execute("""
                SELECT message, response, timestamp, is_user_message 
                FROM chat_history 
                WHERE user_id = %s AND db_name = %s 
                ORDER BY timestamp ASC
            """, (user_id, db_name))
            
            chat_history = []
            for row in cursor.fetchall():
                chat_history.append({
                    "message": row['message'],
                    "response": row['response'],
                    "timestamp": row['timestamp'].isoformat() if row['timestamp'] else None,
                    "is_user_message": bool(row['is_user_message'])
                })
            
            conn.close()
            
            return jsonify({"chat_history": chat_history}), 200
            
        except Exception as e:
            print(f"Error retrieving chat history: {e}")
            import traceback
            traceback.print_exc()
            # Return empty history instead of error
            return jsonify({"chat_history": []}), 200
            
    except Exception as e:
        print(f"❌ ERROR in /get-chat-history: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"chat_history": []}), 200

def generate_chatbot_response(message, db_type, schema, chat_history):
    """Generate chatbot response using Groq AI"""
    try:
        # Use MongoDB-specific prompt if database type is MongoDB
        if db_type.lower() == 'mongodb':
            system_prompt = generate_mongodb_learning_prompt(message, schema, chat_history)
        else:
            # Create context with schema and chat history for SQL databases
            schema_context = create_schema_context(schema, db_type)
            conversation_context = create_conversation_context(chat_history)
            
            # Build the prompt for SQL databases
            system_prompt = f"""You are an expert {db_type.upper()} database assistant. You help users understand their database, write queries, and solve database-related problems.

Database Schema:
{schema_context}

Previous Conversation:
{conversation_context}

Instructions:
1. Be helpful, friendly, and professional
2. Provide clear explanations and guidance
3. When suggesting queries, provide them in code blocks with explanations
4. Focus on teaching and helping users understand database concepts
5. Do NOT offer to execute queries - this is a learning environment only
6. If the user asks to execute a query, explain that they should use the workspace for execution
7. Keep responses concise but informative
8. If you don't know something, say so rather than guessing
9. For {db_type.upper()} queries, use appropriate syntax:
   - MySQL/Cloud: Standard SQL syntax
   - MongoDB: Use db.collection.operation() format (e.g., db.users.find(), db.users.insertOne({{name: "John"}}))

Current user message: {message}

Please provide a helpful response focused on learning and guidance:"""

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        request_body = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [
                {"role": "system", "content": system_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 500,
            "top_p": 1,
            "stream": False
        }
        
        print("Sending request to Groq API...")
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers=headers,
            json=request_body,
            timeout=30
        )
        
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        
        response_data = response.json()
        chatbot_response = response_data['choices'][0]['message']['content'].strip()
        
        # If user asks to execute a query, provide guidance instead
        execute_keywords = ['execute', 'run', 'execute this', 'run this', 'execute the query', 'run the query', 'execute sql', 'run sql']
        if any(keyword in message.lower() for keyword in execute_keywords):
            if db_type.lower() == 'mongodb':
                chatbot_response += "\n\n💡 **Note:** To execute this MongoDB query, please use the workspace area where you can enter queries manually. The chatbot is designed for learning and guidance only."
            else:
                chatbot_response += "\n\n💡 **Note:** To execute this query, please use the workspace area where you can enter SQL queries manually. The chatbot is designed for learning and guidance only."
        
        print(f"Chatbot response generated: {len(chatbot_response)} characters")
        return chatbot_response
        
    except requests.exceptions.ConnectionError as e:
        error_msg = "Network Connection Error: Could not connect to Groq API. Please check your internet connection and DNS settings."
        print(f"❌ ERROR: {error_msg} - {e}")
        raise Exception(error_msg)
    except requests.exceptions.Timeout:
        error_msg = "Request Timed Out: The request to Groq API took too long to respond."
        print(f"❌ ERROR: {error_msg}")
        raise Exception(error_msg)
    except requests.exceptions.HTTPError as e:
        error_msg = f"Groq API Error: {e.response.status_code} - {e.response.text}"
        print(f"❌ ERROR: {error_msg}")
        raise Exception(error_msg)
    except Exception as e:
        print(f"Error generating chatbot response: {e}")
        import traceback
        traceback.print_exc()
        raise Exception(f"An unexpected error occurred while generating the chatbot response: {str(e)}")

def create_schema_context(schema, db_type):
    """Create a readable schema context"""
    if not schema:
        return "No schema information available."
    
    context = f"Database Type: {db_type.upper()}\n\n"
    
    if db_type.lower() == 'mongodb':
        context += "Collections:\n"
        for collection in schema:
            context += f"- {collection['table_name']}:\n"
            for field in collection['columns']:
                context += f"  - {field['name']} ({field['type']})\n"
            context += "\n"
    else:
        context += "Tables:\n"
        for table in schema:
            context += f"- {table['table_name']}:\n"
            for column in table['columns']:
                context += f"  - {column['name']} ({column['type']})"
                if column.get('key') == 'PRI':
                    context += " [PRIMARY KEY]"
                context += "\n"
            context += "\n"
    
    return context

def create_conversation_context(chat_history):
    """Create conversation context from chat history"""
    if not chat_history:
        return "No previous conversation."
    
    context = "Previous messages:\n"
    for i, chat in enumerate(chat_history[-5:], 1):  # Last 5 messages
        if chat.get('is_user_message'):
            context += f"User: {chat['message']}\n"
        else:
            context += f"Assistant: {chat['response']}\n"
    
    return context

def save_chat_message(user_id, db_name, message, response, db_type, is_error=False):
    """Save chat message to database"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if chat_history table exists, create if not
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                db_name VARCHAR(100) NOT NULL,
                message TEXT,
                response TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_user_message BOOLEAN DEFAULT FALSE,
                db_type VARCHAR(20),
                is_error BOOLEAN DEFAULT FALSE
            )
        """)
        conn.commit()
        
        # Save user message
        cursor.execute("""
            INSERT INTO chat_history (user_id, db_name, message, response, timestamp, is_user_message, db_type, is_error)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, db_name, message, response, datetime.now(), True, db_type, is_error))
        
        # Save assistant response
        cursor.execute("""
            INSERT INTO chat_history (user_id, db_name, message, response, timestamp, is_user_message, db_type, is_error)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, db_name, "", response, datetime.now(), False, db_type, is_error))
        
        conn.commit()
        conn.close()
        
        print("Chat messages saved successfully")
        
    except Exception as e:
        print(f"Error saving chat message: {e}")
        import traceback
        traceback.print_exc()
        # Don't fail the request if saving fails

# Remove the execute-chatbot-query route entirely 