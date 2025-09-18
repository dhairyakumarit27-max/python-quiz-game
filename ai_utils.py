import streamlit as st
from groq import Groq

# Initialize Groq client
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def generate_questions(text, num_questions=5):
    """Generate quiz questions from given text using Groq AI"""
    prompt = f"""
    Create {num_questions} multiple choice questions from this text:
    {text}

    Format output as JSON list like:
    [
      {{
        "question": "Q?",
        "options": ["A","B","C","D"],
        "answer": "Correct Answer"
      }}
    ]
    """

    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile"
    )

    return response.choices[0].message.content

def ask_ai(question):
    """Ask chatbot a question"""
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": question}],
        model="llama-3.3-70b-versatile"
    )
    return response.choices[0].message.content
