# ai_utils.py
import streamlit as st
from groq import Groq

@st.cache_resource
def _get_groq_client():
    api_key = st.secrets.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not found in Streamlit secrets.")
    return Groq(api_key=api_key)

def ask_ai(prompt: str, model: str | None = None) -> str:
    """
    Ask Groq and return plain text. Uses model from secrets fallback to
    'llama-3.1-8b-instant' if not present.
    """
    client = _get_groq_client()
    model = model or st.secrets.get("GROQ_MODEL", "llama-3.1-8b-instant")
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        # Return a readable error string so Streamlit doesn't crash
        return f"Error: {e}"
