import os
from groq import Groq

# Make sure your GROQ_API_KEY is set in Streamlit secrets.toml
# Example:
# [general]
# GROQ_API_KEY = "your_api_key_here"

def _get_client():
    """Initialize Groq client using API key from secrets or env variable."""
    api_key = os.environ.get("GROQ_API_KEY") or None
    if not api_key:
        raise ValueError("❌ Missing GROQ_API_KEY. Add it in secrets.toml or environment.")
    return Groq(api_key=api_key)


def generate_questions(text, num_questions=5):
    """
    Generate quiz questions from a given text.
    Returns a list of {question, options, answer}.
    """
    client = _get_client()

    prompt = f"""
    You are a quiz generator. Read the following text and create {num_questions} multiple-choice questions.
    Format the output strictly as JSON with this structure:
    [
      {{
        "question": "string",
        "options": ["A", "B", "C", "D"],
        "answer": "A"
      }},
      ...
    ]

    Text:
    {text}
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
        )
        raw_output = response.choices[0].message.content

        # Try to parse JSON-like output
        import json
        questions = json.loads(raw_output)
        return questions

    except Exception as e:
        print("Error generating questions:", e)
        return []


def ask_ai(prompt):
    """
    General AI assistant to answer user queries.
    Returns plain text.
    """
    client = _get_client()
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"
