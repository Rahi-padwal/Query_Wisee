import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv('GROQ_API_KEY')

if not api_key:
    print("❌ No API key found in .env file")
    exit(1)

print(f"🔑 API Key loaded (length: {len(api_key)})")
print(f"🔑 API Key starts with: {api_key[:10]}...")

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
    print("🚀 Testing API key with Groq...")
    response = requests.post(
        'https://api.groq.com/openai/v1/chat/completions',
        headers=headers,
        json=data,
        timeout=10
    )
    
    print(f"📊 Response status: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ API key is working correctly!")
        result = response.json()
        if 'choices' in result and result['choices']:
            print(f"📝 Response: {result['choices'][0]['message']['content']}")
    elif response.status_code == 401:
        print("❌ API key is invalid or expired")
        print(f"📄 Error details: {response.text}")
    else:
        print(f"⚠️ Unexpected response: {response.status_code}")
        print(f"📄 Response: {response.text}")
        
except Exception as e:
    print(f"❌ Error testing API: {e}") 