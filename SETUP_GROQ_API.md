# Groq API Setup Guide

To use the Groq API for query conversion features, follow these steps:

## 1. Get a Groq API Key

1. Go to [https://console.groq.com/](https://console.groq.com/)
2. Sign up or log in to your account
3. Navigate to the API Keys section
4. Create a new API key
5. Copy the API key (it starts with `gsk_`)

## 2. Configure the API Key

### Option A: Using Environment Variables (Recommended)

Create a `.env` file in your project root:

```bash
GROQ_API_KEY=gsk_your_actual_api_key_here
```

### Option B: Set Environment Variable Directly

**Windows (PowerShell):**
```powershell
$env:GROQ_API_KEY="gsk_your_actual_api_key_here"
```

**Windows (Command Prompt):**
```cmd
set GROQ_API_KEY=gsk_your_actual_api_key_here
```

**Linux/Mac:**
```bash
export GROQ_API_KEY=gsk_your_actual_api_key_here
```

## 3. Install Required Package

Make sure you have the `python-dotenv` package installed:

```bash
pip install python-dotenv
```

## 4. Restart Your Application

After setting up the API key, restart your Flask application:

```bash
python app.py
```

## 5. Test the Features

Once configured, you can use:
- **Convert to English**: Convert SQL/MongoDB queries to plain English
- **Convert to SQL/MongoDB**: Convert English descriptions to queries

## Troubleshooting

- **401 Unauthorized**: Check if your API key is correct
- **429 Rate Limit**: You've exceeded the API rate limit, try again later
- **Missing API Key**: Make sure the `GROQ_API_KEY` environment variable is set

## Note

The Groq API provides free tier usage with generous limits. Check their pricing page for current limits and costs. 