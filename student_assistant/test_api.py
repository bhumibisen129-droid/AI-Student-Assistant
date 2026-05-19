import requests
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GROQ_API_KEY", "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")
print(f"Key found: {api_key[:15]}..." if api_key else "❌ Key not found!")

response = requests.post(
    "https://api.groq.com/openai/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    },
    json={
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": "Say hello"}],
        "max_tokens": 100
    },
    timeout=20,
)

print(f"Status: {response.status_code}")
print(f"Full Error: {response.text}")