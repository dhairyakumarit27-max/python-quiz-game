from groq import Groq
import streamlit as st

# --- Cached Groq Client ---
@st.cache_resource
def get_groq_client():
    api_key = st.secrets.get("GROQ_API_KEY")
    if not api_key:
        st.error("Groq API key not found in secrets.toml")
        st.stop()
    return Groq(api_key=api_key)

# --- Ask AI Function ---
def ask_ai(prompt: str) -> str:
    client = get_groq_client()
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",   # ✅ Updated model ID
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"
