#!/usr/bin/env python3
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("dotenv loaded successfully")
except ImportError:
    print("python-dotenv not installed")

print(f"GEMINI_API_KEY from env: {os.getenv('GEMINI_API_KEY')}")
print(f"REPLICATE_API_KEY from env: {os.getenv('REPLICATE_API_KEY')}")
print(f"OLLAMA_BASE_URL from env: {os.getenv('OLLAMA_BASE_URL')}")

# También verificar si ai_services puede acceder a las keys
try:
    from utils.ai_services import get_available_providers_info
    providers = get_available_providers_info()
    print("\n=== PROVIDERS INFO ===")
    for name, info in providers.items():
        print(f"{name}: configured={info['configured']}, status={info['status']}")
except Exception as e:
    print(f"Error loading ai_services: {e}")