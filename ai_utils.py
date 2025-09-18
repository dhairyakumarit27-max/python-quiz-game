from groq import Groq
import streamlit as st

# Cached Groq client
@st.cache_resource
def get_groq_client():
    api_key = st.secrets.get("GROQ_API_KEY")
    if not api_key:
        st.error("Groq API key not found in secrets.toml")
        st.stop()
    return Groq(api_key=api_key)

# Ask AI helper
def ask_ai(prompt: str) -> str:
    client = get_groq_client()
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",  # or another model you have
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"
