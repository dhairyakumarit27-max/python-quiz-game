import os
from groq import Groq

# Setup Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# AI Assistant Chatbot
def ask_ai(query):
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": query}],
    )
    return response.choices[0].message.content
