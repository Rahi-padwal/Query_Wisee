import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv('GROQ_API_KEY')

if not api_key:
    exit(1)

# Test the API key
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

data = {
    "model": "meta-llama/llama-4-scout-17b-16e-instruct",
    "messages": [
        {"role": "user", "content": "Hello, this is a test message."}
    ],
    "max_tokens": 50
}

try:
    response = requests.post(
        'https://api.groq.com/openai/v1/chat/completions',
        headers=headers,
        json=data,
        timeout=10
    )
    
    if response.status_code == 200:
        result = response.json()
        if 'choices' in result and result['choices']:
            pass
    elif response.status_code == 401:
        pass
    else:
        pass
        
except Exception as e:
    pass 