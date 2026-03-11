from google import genai
import os

# Initialize client
api_key = "your-api-key"
client = genai.Client(api_key=api_key)

# List all available models
print("Available models:")
for model in client.models.list():
    print(f"- {model.name}")