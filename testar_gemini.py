import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

modelo = os.getenv("GEMINI_MODEL")

print("Modelo:", modelo)

response = client.models.generate_content(
    model=modelo,
    contents="Responda apenas: MODELO FUNCIONANDO"
)

print(response.text)