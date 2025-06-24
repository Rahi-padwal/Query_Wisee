def generate_english_to_sql_prompt(english_query: str, schema: list) -> str:
    """
    Generate a prompt for converting English to SQL using the given schema.
    
    Args:
        english_query (str): The English query to convert
        schema (list): List of tables and their columns
        
    Returns:
        str: Formatted prompt for the model
    """
    prompt = """You are a SQL expert. Convert the following English question into a valid SQL query.
The query should be syntactically correct and use the provided database schema.
Return ONLY the SQL query without any explanations or additional text. Please provide the query with lowest complexity(easiest).

IMPORTANT: Prefix your SQL query with "-- SQL" comment.

English Question: {english_query}

Database Schema:
{schema_text}

SQL Query:"""
    
    # Format schema text
    schema_text = ""
    for table in schema:
        schema_text += f"Table: {table['table_name']}\n"
        schema_text += "Columns:\n"
        for column in table['columns']:
            schema_text += f"- {column['name']} ({column['type']})\n"
        schema_text += "\n"
    
    return prompt.format(english_query=english_query, schema_text=schema_text)

def generate_english_to_mongodb_prompt(english_query: str, schema: list) -> str:
    """
    Generate a prompt for converting English to MongoDB queries using the given schema.
    
    Args:
        english_query (str): The English query to convert
        schema (list): List of collections and their fields
        
    Returns:
        str: Formatted prompt for the model
    """
    prompt = """You are a MongoDB expert. Convert the following English question into a valid MongoDB query.
The query should be syntactically correct and use the provided database schema.
Return ONLY the MongoDB query without any explanations or additional text. Please provide the query with lowest complexity(easiest).

IMPORTANT: Prefix your MongoDB query with "// MongoDB" comment.

English Question: {english_query}

Database Schema:
{schema_text}

MongoDB Query:"""
    
    # Format schema text for MongoDB
    schema_text = ""
    for collection in schema:
        schema_text += f"Collection: {collection['table_name']}\n"
        schema_text += "Fields:\n"
        for field in collection['columns']:
            schema_text += f"- {field['name']} ({field['type']})\n"
        schema_text += "\n"
    
    return prompt.format(english_query=english_query, schema_text=schema_text)

def generate_sql_to_english_prompt(sql_query: str, schema: list) -> str:
    """
    Generate a prompt for converting SQL to English using the given schema.
    
    Args:
        sql_query (str): The SQL query to convert
        schema (list): List of tables and their columns
        
    Returns:
        str: Formatted prompt for the model
    """
    prompt = """You are a SQL expert. Convert the following SQL query into a clear and concise English description.
Focus ONLY on these three aspects:

1. Purpose: What does this query do? (One clear sentence)
2. Tables: If used in the query, tell which tables are involved and how are they related? (List the tables)
3. Conditions: If any related to query, tell what are the main filters and conditions? (List the key conditions)

Keep your response brief and to the point. Format it exactly like this:

Purpose: [One sentence explaining what the query does]

Tables: 
- [Table 1]
- [Table 2]
...

Conditions:
- [Condition 1]
- [Condition 2]
...

SQL Query: {sql_query}

Database Schema:
{schema_text}

English Description:"""
    
    # Format schema text
    schema_text = ""
    for table in schema:
        schema_text += f"Table: {table['table_name']}\n"
        schema_text += "Columns:\n"
        for column in table['columns']:
            schema_text += f"- {column['name']} ({column['type']})\n"
        schema_text += "\n"
    
    return prompt.format(sql_query=sql_query, schema_text=schema_text)

def generate_mongodb_to_english_prompt(mongodb_query: str, schema: list) -> str:
    """
    Generate a prompt for converting MongoDB queries to English using the given schema.
    
    Args:
        mongodb_query (str): The MongoDB query to convert
        schema (list): List of collections and their fields
        
    Returns:
        str: Formatted prompt for the model
    """
    prompt = """You are a MongoDB expert. Convert the following MongoDB query into a clear and concise English description.
Focus ONLY on these three aspects:

1. Purpose: What does this query do? (One clear sentence)
2. Collections: If used in the query, tell which collections are involved? (List the collections)
3. Conditions: If any related to query, tell what are the main filters and conditions? (List the key conditions)

Keep your response brief and to the point. Format it exactly like this:

Purpose: [One sentence explaining what the query does]

Collections: 
- [Collection 1]
- [Collection 2]
...

Conditions:
- [Condition 1]
- [Condition 2]
...

MongoDB Query: {mongodb_query}

Database Schema:
{schema_text}

English Description:"""
    
    # Format schema text for MongoDB
    schema_text = ""
    for collection in schema:
        schema_text += f"Collection: {collection['table_name']}\n"
        schema_text += "Fields:\n"
        for field in collection['columns']:
            schema_text += f"- {field['name']} ({field['type']})\n"
        schema_text += "\n"
    
    return prompt.format(mongodb_query=mongodb_query, schema_text=schema_text)

def generate_mongodb_learning_prompt(user_message: str, schema: list, chat_history: list = None) -> str:
    """
    Generate a MongoDB-specific learning prompt for the chatbot.
    
    Args:
        user_message (str): The user's message
        schema (list): List of collections and their fields
        chat_history (list): Previous conversation history
        
    Returns:
        str: Formatted prompt for MongoDB learning
    """
    # Create conversation context
    conversation_context = ""
    if chat_history:
        conversation_context = "Previous conversation:\n"
        for chat in chat_history[-3:]:  # Last 3 messages
            if chat.get('is_user_message'):
                conversation_context += f"User: {chat['message']}\n"
            else:
                conversation_context += f"Assistant: {chat['response']}\n"
        conversation_context += "\n"
    
    # Format schema for MongoDB
    schema_text = ""
    for collection in schema:
        schema_text += f"Collection: {collection['table_name']}\n"
        schema_text += "Fields:\n"
        for field in collection['columns']:
            schema_text += f"- {field['name']} ({field['type']})\n"
        schema_text += "\n"
    
    prompt = f"""You are an expert MongoDB database assistant. You help users understand MongoDB, write queries, and solve database-related problems.

Database Schema:
{schema_text}

{conversation_context}

Instructions:
1. Be helpful, friendly, and professional
2. Provide clear explanations and guidance specific to MongoDB
3. When suggesting queries, provide them in MongoDB syntax with explanations
4. Focus on teaching MongoDB concepts like:
   - Document-based data structure
   - CRUD operations (find, insert, update, delete)
   - Aggregation pipeline
   - Indexing and performance
   - BSON data types
5. Do NOT offer to execute queries - this is a learning environment only
6. If the user asks to execute a query, explain that they should use the workspace for execution
7. Keep responses concise but informative
8. If you don't know something, say so rather than guessing
9. Use proper MongoDB syntax examples:
   - db.collection.find({{"field": "value"}})
   - db.collection.insertOne({{"name": "John", "age": 30}})
   - db.collection.updateOne({{"_id": ObjectId("...")}}, {{"$set": {{"field": "new_value"}}}})
   - db.collection.deleteOne({{"field": "value"}})
   - db.collection.aggregate([{{"$match": {{"field": "value"}}}}, {{"$group": {{"_id": "$field", "count": {{"$sum": 1}}}}}}])

Current user message: {user_message}

Please provide a helpful MongoDB-focused response for learning and guidance:"""
    
    return prompt 

def generate_workspace_mongodb_prompt(english_query: str, schema: list) -> str:
    """
    Generate a workspace-specific prompt for converting English to MongoDB queries.
    This function is specifically designed for the workspace area to ensure MongoDB syntax.
    
    Args:
        english_query (str): The English query to convert
        schema (list): List of collections and their fields
        
    Returns:
        str: Formatted prompt for the model
    """
    prompt = """You are a MongoDB expert. Convert the following English question into a valid MongoDB query.
The query should be syntactically correct and use the provided database schema.
Return ONLY the MongoDB query without any explanations or additional text. Please provide the query with lowest complexity(easiest).

IMPORTANT: Prefix your MongoDB query with "// MongoDB" comment.

English Question: {english_query}

Database Schema:
{schema_text}

MongoDB Query:"""
    
    # Format schema text for MongoDB
    schema_text = ""
    for collection in schema:
        schema_text += f"Collection: {collection['table_name']}\n"
        schema_text += "Fields:\n"
        for field in collection['columns']:
            schema_text += f"- {field['name']} ({field['type']})\n"
        schema_text += "\n"
    
    return prompt.format(english_query=english_query, schema_text=schema_text) 