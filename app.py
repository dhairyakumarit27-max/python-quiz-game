# =========================================================
# FINAL APP.PY - QUIZ + AI CHATBOT
# =========================================================

import streamlit as st
import random
import time
import json
import gspread
import pandas as pd
from gspread.exceptions import SpreadsheetNotFound
from google.oauth2.service_account import Credentials
from ai_utils import ask_ai
from streamlit_autorefresh import st_autorefresh

# =========================================================
# --- THEME START ---
def apply_custom_theme():
    st.markdown(
        """
        <style>
        body, .stApp { background-color: #FFFFFF; color: #000000; }
        .stButton>button {
            background-color: #4B9CD3; color: #FFFFFF;
            border-radius: 8px; border: none; padding: 0.5em 1em; font-weight: bold;
        }
        .stButton>button:hover { background-color: #357ABD; }
        .quiz-option { border: 2px solid #4B9CD3; border-radius: 12px;
            padding: 1em; margin: 0.5em 0; cursor: pointer; background-color: #F9F9F9;
            transition: all 0.2s ease-in-out; }
        .quiz-option:hover { background-color: #E6F0FA; border-color: #357ABD; }
        .quiz-option.selected { background-color: #4B9CD3; color: #FFFFFF; font-weight: bold; }
        </style>
        """,
        unsafe_allow_html=True
    )
apply_custom_theme()
# --- THEME END ---
# =========================================================

st.set_page_config(page_title="Quiz Championship", layout="centered")
st.title("🧠 Fun Quiz Game")

# =========================================================
# --- GOOGLE SHEETS START ---
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client

@st.cache_resource
def open_sheet(sheet_name="QuizResults"):
    client = get_gspread_client()
    try:
        sh = client.open(sheet_name)
    except SpreadsheetNotFound:
        st.error(f"Spreadsheet '{sheet_name}' not found. Share with service account email.")
        st.stop()
    return sh.sheet1

def ensure_headers(worksheet):
    headers = ["Name", "Email", "Category", "Score"]
    existing = worksheet.row_values(1)
    if existing != headers:
        worksheet.clear()
        worksheet.append_row(headers, value_input_option="USER_ENTERED")
# --- GOOGLE SHEETS END ---
# =========================================================

# =========================================================
# --- QUIZ DATA START ---
quiz_data = {
    "Math": [
        {"question": "5 + 3 = ?", "options": ["6", "7", "8", "9"], "answer": "8"},
        {"question": "10 - 6 = ?", "options": ["2", "4", "6", "8"], "answer": "4"},
        {"question": "3 × 3 = ?", "options": ["6", "9", "12", "15"], "answer": "9"},
        {"question": "5 + 3 = ?", "options": ["6", "7", "8", "9"], "answer": "8"},
        {"question": "12 ÷ 4 = ?", "options": ["2", "3", "4", "5"], "answer": "3"},
    ],
    "Science": [
        {"question": "H2O is?", "options": ["Water", "Oxygen", "Hydrogen", "Salt"], "answer": "Water"},
        {"question": "Earth revolves around?", "options": ["Moon", "Mars", "Sun", "Venus"], "answer": "Sun"},
        {"question": "Force unit?", "options": ["Newton", "Joule", "Watt", "Volt"], "answer": "Newton"},
        {"question": "What planet is known as the Red Planet?", "options": ["Earth", "Mars", "Jupiter", "Venus"], "answer": "Mars"},
        {"question": "H2O is the chemical formula for what?", "options": ["Oxygen", "Hydrogen", "Water", "Carbon dioxide"], "answer": "Water"},
    ]
}
# --- QUIZ DATA END ---
# =========================================================

# =========================================================
# --- SESSION STATE INIT ---
if "user" not in st.session_state:
    st.session_state.user = None
if "questions" not in st.session_state:
    st.session_state.questions = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
# --- SESSION STATE END ---
# =========================================================

# =========================================================
# --- QUIZ LOGIC START ---
def run_quiz():
    st.sidebar.title("📜 Quiz Rules")
    st.sidebar.write("""
    - Enter **Name & Email** to register    
    - Choose a category    
    - **10 seconds** allowed per question    
    - Scores saved to Google Sheets + leaderboard  
    """)

    # --- Registration ---
    if not st.session_state.user:
        st.title("📝 Player Registration")
        name = st.text_input("Enter your Name")
        email = st.text_input("Enter your Email")
        if st.button("Start Quiz"):
            if name.strip() and email.strip():
                st.session_state.user = {"name": name.strip(), "email": email.strip()}
                st.session_state.score = 0
                st.session_state.q_index = 0
                st.session_state.start_time = None
            else:
                st.error("Please provide both Name and Email.")
        st.stop()

    # --- Category Selection ---
    st.title("🎯 Professional Quiz Championship")
    category = st.selectbox("Choose a Category", list(quiz_data.keys()))

    # --- Prepare Questions ---
    if st.session_state.get("active_category") != category:
        st.session_state.questions = random.sample(quiz_data[category], len(quiz_data[category]))
        st.session_state.active_category = category
        st.session_state.q_index = 0
        st.session_state.score = 0
        st.session_state.start_time = None

    questions = st.session_state.questions

    # --- Timer refresh ---
    st_autorefresh(interval=1000, key="quiz_refresh")

    # --- Question Loop ---
    if st.session_state.q_index < len(questions):
        q = questions[st.session_state.q_index]
        st.subheader(f"Question {st.session_state.q_index + 1} of {len(questions)}")
        st.write(q["question"])

        if st.session_state.start_time is None:
            st.session_state.start_time = time.time()

        time_left = 10 - int(time.time() - st.session_state.start_time)
        st.markdown(f"**⏱ Time left:** {max(time_left, 0)} seconds")

        if time_left <= 0:
            st.warning("⏰ Time’s up! No points awarded.")
            st.session_state.q_index += 1
            st.session_state.start_time = None
            st.rerun()

        choice = st.radio("Options", q["options"], key=f"opt_{st.session_state.q_index}")

        if st.button("Submit Answer", key=f"submit_{st.session_state.q_index}"):
           if choice == q["answer"]:
              st.session_state.score += 1
              st.success("✅ Correct!")
           else:
              st.error(f"❌ Wrong! Correct answer: {q['answer']}")

    # --- pause to show feedback ---
          time.sleep(2)

    # --- move to next question ---
         st.session_state.q_index += 1
         st.session_state.start_time = None
         st.rerun()



    else:
        st.success(f"🏆 Quiz Over! {st.session_state.user['name']}, "
                   f"your score: {st.session_state.score}/{len(questions)}")

        # Save score once
        if "score_saved" not in st.session_state:
            st.session_state.score_saved = False
            st.session_state.worksheet_cache = None

        if not st.session_state.score_saved:
            try:
                worksheet = open_sheet("QuizResults")
                ensure_headers(worksheet)
                worksheet.append_row(
                    [st.session_state.user["name"],
                     st.session_state.user["email"],
                     st.session_state.active_category,
                     st.session_state.score],
                    value_input_option="USER_ENTERED"
                )
                st.session_state.worksheet_cache = worksheet
                st.session_state.score_saved = True
            except Exception as e:
                st.error(f"Error saving score: {e}")

        # Leaderboard
        st.subheader("🏅 Top 5 Players")
        try:
            worksheet = st.session_state.worksheet_cache or open_sheet("QuizResults")
            records = worksheet.get_all_records()
            if records:
                df = pd.DataFrame(records)
                df["Score"] = pd.to_numeric(df["Score"], errors="coerce").fillna(0).astype(int)
                top5 = df.sort_values("Score", ascending=False).head(5)
                st.table(top5[["Name", "Score", "Category"]])
            else:
                st.write("No scores yet.")
        except Exception as e:
            st.error(f"Error loading leaderboard: {e}")

        if st.button("Play Again"):
            st.session_state.user = None
            st.session_state.score_saved = False
            st.rerun()
# --- QUIZ LOGIC END ---
# =========================================================

# =========================================================
# --- MAIN MENU START ---
st.sidebar.markdown("---")
menu = ["Quiz", "AI Assistant"]
choice = st.sidebar.selectbox("Menu", menu, index=0)

if choice == "Quiz":
    run_quiz()

elif choice == "AI Assistant":
    st.header("🤖 AI Assistant Chatbot")
    user_q = st.text_input("Ask me anything:", key="ai_chat_input")
    if st.button("Ask AI", key="ai_chat_button"):
        if user_q.strip():
            with st.spinner("Thinking..."):
                try:
                    answer = ask_ai(user_q)
                    st.session_state.chat_history.append(("🧑 You", user_q))
                    st.session_state.chat_history.append(("🤖 AI", answer))
                except Exception as e:
                    st.error(f"AI Error: {e}")
        else:
            st.warning("Please type a question.")

    if st.button("Clear Chat", key="ai_clear_chat"):
        st.session_state.chat_history = []

    for sender, msg in reversed(st.session_state.chat_history):
        st.markdown(f"**{sender}:** {msg}")
# --- MAIN MENU END ---
# =========================================================
