import streamlit as st
import random
import time
import json
import gspread
import pandas as pd
from gspread.exceptions import SpreadsheetNotFound
from google.oauth2.service_account import Credentials

# ---------- Google Sheets client helper ----------
def get_gspread_client():
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict)
    client = gspread.authorize(creds)
    return client

def open_sheet(sheet_name):
    client = get_gspread_client()
    sheet = client.open("QuizAppDB")  # replace with your sheet name
    return sheet.worksheet(sheet_name)


# ---------- START: Save Results (with duplicate check) ----------
def save_result(name, score):
    worksheet = open_sheet("QuizResults")
    existing = worksheet.col_values(1)  # col A = names
    if name not in existing:  # prevent duplicates
        worksheet.append_row([name, score, time.strftime("%Y-%m-%d %H:%M:%S")])
# ---------- END: Save Results (with duplicate check) ----------


# ---------- START: Leaderboard Helper (cached) ----------
@st.cache_data(ttl=30)  # cache for 30 seconds
def load_leaderboard():
    worksheet = open_sheet("QuizResults")
    data = worksheet.get_all_records()
    return data
# ---------- END: Leaderboard Helper (cached) ----------


# ---------- Quiz Section ----------
def run_quiz():
    st.subheader("📝 Take the Quiz")

    name = st.text_input("Enter your name:")
    if not name:
        st.warning("Please enter your name to start the quiz.")
        return

    if "score" not in st.session_state:
        st.session_state.score = 0
        st.session_state.qn = 0

    questions = [
        ("What is 2+2?", ["3", "4", "5"], "4"),
        ("Capital of France?", ["London", "Berlin", "Paris"], "Paris"),
        ("What is 5*3?", ["15", "10", "20"], "15"),
    ]

    if st.session_state.qn < len(questions):
        q, opts, ans = questions[st.session_state.qn]
        st.write(f"**Q{st.session_state.qn+1}: {q}**")
        choice = st.radio("Options", opts, key=f"q{st.session_state.qn}")

        if st.button("Submit Answer"):
            if choice == ans:
                st.session_state.score += 1
            st.session_state.qn += 1
            st.experimental_rerun()
    else:
        st.success(f"Quiz finished! Your Score: {st.session_state.score}/{len(questions)}")
        save_result(name, st.session_state.score)


# ---------- Leaderboard Section ----------
def show_leaderboard():
    st.subheader("🏆 Leaderboard")

    # ---------- START: Refresh Button ----------
    if st.button("🔄 Refresh Leaderboard"):
        st.cache_data.clear()
    # ---------- END: Refresh Button ----------

    data = load_leaderboard()
    if data:
        df = pd.DataFrame(data)
        st.table(df)
    else:
        st.info("No results yet!")


# ---------- AI Chatbot Section ----------
def ai_chatbot():
    st.subheader("🤖 AI Chat Assistant")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    user_input = st.text_input("You:", key="chat_input")
    if st.button("Send"):
        if user_input.strip():
            # Append user message
            st.session_state.chat_history.append(("You", user_input))

            # ---------- Replace with correct Groq model ----------
            from groq import Groq
            client = Groq(api_key=st.secrets["GROQ_API_KEY"])

            try:
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",  # ✅ updated model
                    messages=[{"role": "user", "content": user_input}]
                )
                reply = response.choices[0].message.content
            except Exception as e:
                reply = f"Error: {e}"

            st.session_state.chat_history.append(("🤖 AI", reply))
            st.experimental_rerun()

    # ---------- Show chat in reverse (newest at bottom) ----------
    for role, msg in st.session_state.chat_history:
        st.write(f"**{role}:** {msg}")


# ---------- Main Menu ----------
st.title("🎓 School Quiz + AI Assistant")

menu = ["Quiz", "Leaderboard", "AI Chatbot"]
choice = st.sidebar.selectbox("Navigate", menu)

if choice == "Quiz":
    run_quiz()
elif choice == "Leaderboard":
    show_leaderboard()
elif choice == "AI Chatbot":
    ai_chatbot()
