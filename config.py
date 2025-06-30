# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Groq API Configuration
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# Debug: Print API key status (without showing the actual key)
if GROQ_API_KEY:
    print(f"✓ GROQ_API_KEY loaded successfully (length: {len(GROQ_API_KEY)})")
    if GROQ_API_KEY.startswith('gsk_'):
        print("✓ API key format looks correct (starts with 'gsk_')")
    else:
        print("⚠ API key format may be incorrect (should start with 'gsk_')")
else:
    print("✗ GROQ_API_KEY not found in environment variables")

# Database Configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'ai_sql_assistant')

# Flask Configuration
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')