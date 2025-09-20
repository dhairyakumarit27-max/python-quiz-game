import streamlit as st
import random
import time
import json
import gspread
from google.oauth2.service_account import Credentials
from groq import Groq
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import pandas as pd

# ==============================
# Google Sheets Setup
# ==============================
def get_gspread_client():
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds)

def open_sheet(worksheet_name="Leaderboard"):
    client = get_gspread_client()
    workbook_name = st.secrets.get("GSHEET_NAME", "QuizAppDB")
    book = client.open(workbook_name)

    try:
        worksheet = book.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = book.add_worksheet(title=worksheet_name, rows="100", cols="10")
        worksheet.append_row(["Name", "Score", "Timestamp"])
    return worksheet

def save_result(name, score):
    """Save result directly to Google Sheet (once at quiz end)."""
    worksheet = open_sheet("Leaderboard")
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    worksheet.append_row([str(name), int(score), timestamp])

def load_leaderboard(limit=50):
    """Load leaderboard from Google Sheet."""
    worksheet = open_sheet("Leaderboard")
    data = worksheet.get_all_records()
    if not data:
        return pd.DataFrame(columns=["Name", "Score", "Timestamp"])
    df = pd.DataFrame(data)
    if "Score" in df.columns:
        df = df.sort_values(by="Score", ascending=False).head(limit)
    return df

# ==============================
# Quiz Questions
# ==============================
QUIZ_QUESTIONS = {
    "Maths": [
        {"question": "5 + 3 = ?", "options": ["6", "7", "8", "9"], "answer": "8"},
        {"question": "12 ÷ 4 = ?", "options": ["2", "3", "4", "6"], "answer": "3"},
        {"question": "15 - 7 = ?", "options": ["6", "7", "8", "9"], "answer": "8"},
        {"question": "9 × 2 = ?", "options": ["16", "18", "20", "22"], "answer": "18"},
        {"question": "100 ÷ 10 = ?", "options": ["5", "10", "15", "20"], "answer": "10"},
    ],
    "Science": [
        {"question": "What planet is known as the Red Planet?",
         "options": ["Earth", "Mars", "Jupiter", "Venus"], "answer": "Mars"},
        {"question": "Which gas do humans need to breathe?",
         "options": ["Oxygen", "Carbon Dioxide", "Nitrogen", "Helium"], "answer": "Oxygen"},
        {"question": "What is H2O commonly known as?",
         "options": ["Oxygen", "Hydrogen", "Water", "Salt"], "answer": "Water"},
        {"question": "Which organ pumps blood in the human body?",
         "options": ["Lungs", "Brain", "Heart", "Liver"], "answer": "Heart"},
        {"question": "Which part of the plant makes food?",
         "options": ["Root", "Stem", "Leaf", "Flower"], "answer": "Leaf"},
    ]
}

# ==============================
# AI Assistant Setup
# ==============================
def get_groq_client():
    return Groq(api_key=st.secrets["GROQ_API_KEY"])

def chat_with_ai(user_input, history):
    client = get_groq_client()
    messages = [{"role": "system", "content": "You are a helpful school assistant."}]
    for h in history:
        messages.append({"role": "user", "content": h["user"]})
        messages.append({"role": "assistant", "content": h["ai"]})
    messages.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
    )
    return response.choices[0].message.content

# ==============================
# Quiz Logic
# ==============================
def run_quiz():
    # --- Registration ---
    if "registered" not in st.session_state:
        st.session_state.registered = False
    if "result_saved" not in st.session_state:
        st.session_state.result_saved = False  # ✅ ensure save only once

    if not st.session_state.registered:
        st.subheader("📝 Register to Start Quiz")
        name = st.text_input("Enter your name:", key="reg_name")
        category = st.selectbox("Choose Category", ["Maths", "Science"], key="reg_cat")
        if st.button("Start Quiz"):
            if name.strip():
                st.session_state.name = name.strip()
                st.session_state.category = category
                st.session_state.questions = random.sample(QUIZ_QUESTIONS[category], 5)
                st.session_state.q_index = 0
                st.session_state.score = 0
                st.session_state.start_time = None
                st.session_state.feedback = None
                st.session_state.result_saved = False
                st.session_state.registered = True
                st.rerun()
            else:
                st.warning("Please enter your name to continue.")
        return

    # --- Quiz Finished ---
    if st.session_state.q_index >= len(st.session_state.questions):
        st.success(f"🎉 Quiz finished! Your score: {st.session_state.score}/{len(st.session_state.questions)}")

        # ✅ Save result only once, when quiz is over
        if not st.session_state.result_saved:
            try:
                save_result(st.session_state.name, st.session_state.score)
                st.session_state.result_saved = True
            except Exception as e:
                st.error(f"Could not save score to leaderboard: {e}")

        st.header("🏆 Leaderboard (Top 5)")
        try:
            leaderboard = load_leaderboard()
            if not leaderboard.empty:
                st.dataframe(leaderboard.reset_index(drop=True).head(5))
            else:
                st.info("Leaderboard is empty.")
        except Exception as e:
            st.error(f"Error loading leaderboard: {e}")

        if st.button("Play Again"):
            st.session_state.registered = False
            st.session_state.result_saved = False
            st.rerun()
        return

    # --- Current Question ---
    q = st.session_state.questions[st.session_state.q_index]
    if st.session_state.get("start_time") is None:
        st.session_state.start_time = time.time()

    elapsed = int(time.time() - st.session_state.start_time)
    remaining = max(0, 10 - elapsed)

    st.write(f"⏳ Time left: {remaining} sec")

    # Auto-refresh every second while question is active
    if remaining > 0:
        st_autorefresh(interval=1000, key=f"refresh_{st.session_state.q_index}")

    if remaining <= 0 and not st.session_state.get("feedback"):
        st.session_state.feedback = "⏰ Time’s up! No points awarded."
        st.session_state.q_index += 1
        st.session_state.start_time = None
        st.rerun()

    st.subheader(f"Question {st.session_state.q_index + 1}")
    st.write(q["question"])
    choice = st.radio("Options:", q["options"], key=f"q{st.session_state.q_index}")

    if st.button("Submit Answer", key=f"submit_{st.session_state.q_index}"):
        if choice == q["answer"]:
            st.session_state.score += 1
            st.session_state.feedback = "✅ Correct!"
        else:
            st.session_state.feedback = f"❌ Wrong! Correct answer: {q['answer']}"
        st.session_state.q_index += 1
        st.session_state.start_time = None
        st.rerun()

    if st.session_state.get("feedback"):
        st.info(st.session_state.feedback)
        st.session_state.feedback = None

# ==============================
# Streamlit Layout
# ==============================
st.set_page_config(layout="wide")

st.sidebar.title("📘 Rules")
st.sidebar.markdown("""
- You have **10 seconds** for each question.  
- Once you submit, the answer is final.  
- Score is saved to the leaderboard **after the quiz ends**.  
- Be honest & have fun! 🎉
""")

col1, col2 = st.columns([2, 1])

with col1:
    st.title("🎯 School Quiz Game")
    try:
        run_quiz()
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")

with col2:
    st.title("🤖 AI Assistant")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    user_input = st.text_input("Ask me anything:", key="chat_input")
    if st.button("Send"):
        if user_input:
            try:
                ai_reply = chat_with_ai(user_input, st.session_state.chat_history)
            except Exception as e:
                ai_reply = f"(AI error: {e})"
            st.session_state.chat_history.append({"user": user_input, "ai": ai_reply})

    for chat in reversed(st.session_state.chat_history):
        st.markdown(f"**You:** {chat['user']}")
        st.markdown(f"**AI:** {chat['ai']}")
