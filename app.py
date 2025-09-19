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

# ---------- QUIZ UI SETUP + THEME ----------
def apply_custom_theme():
    st.markdown(
        """
        <style>
        body, .stApp {
            background-color: #FFFFFF;
            color: #000000;
        }
        .stButton>button {
            background-color: #4B9CD3;
            color: #FFFFFF;
            border-radius: 8px;
            border: none;
            padding: 0.5em 1em;
            font-weight: bold;
        }
        .stButton>button:hover {
            background-color: #357ABD;
        }
        .quiz-option {
            border: 2px solid #4B9CD3;
            border-radius: 12px;
            padding: 1em;
            margin: 0.5em 0;
            cursor: pointer;
            background-color: #F9F9F9;
            transition: all 0.2s ease-in-out;
        }
        .quiz-option:hover {
            background-color: #E6F0FA;
            border-color: #357ABD;
        }
        .quiz-option.selected {
            background-color: #4B9CD3;
            color: #FFFFFF;
            font-weight: bold;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

apply_custom_theme()

# ---------- Google Sheets client helper ----------
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client

def open_sheet(sheet_name="QuizResults"):
    client = get_gspread_client()
    try:
        sh = client.open(sheet_name)
    except SpreadsheetNotFound:
        st.error(f"Spreadsheet '{sheet_name}' not found. Share it with your service account email.")
        st.stop()
    return sh.sheet1

def ensure_headers(worksheet):
    headers = ["Name", "Email", "Category", "Score"]
    existing = worksheet.row_values(1)
    if existing != headers:
        worksheet.clear()
        worksheet.append_row(headers, value_input_option="USER_ENTERED")

# ---------- Quiz data ----------
quiz_data = {
    "Math": [
        {"question": "5 + 3 = ?", "options": ["6", "7", "8", "9"], "answer": "8"},
        {"question": "10 - 6 = ?", "options": ["2", "4", "6", "8"], "answer": "4"},
        {"question": "3 × 3 = ?", "options": ["6", "9", "12", "15"], "answer": "9"},
        {"question": "12 ÷ 4 = ?", "options": ["2", "3", "4", "6"], "answer": "3"},
        {"question": "7 + 2 = ?", "options": ["8", "9", "10", "11"], "answer": "9"},
    ],
    "General Knowledge": [
        {"question": "Capital of France?", "options": ["Berlin", "Paris", "London", "Madrid"], "answer": "Paris"},
        {"question": "Which planet is called Red Planet?", "options": ["Earth", "Jupiter", "Mars", "Saturn"], "answer": "Mars"},
        {"question": "Who wrote Hamlet?", "options": ["Dickens", "Shakespeare", "Tolstoy", "Twain"], "answer": "Shakespeare"},
        {"question": "Largest ocean?", "options": ["Atlantic", "Pacific", "Indian", "Arctic"], "answer": "Pacific"},
        {"question": "Fastest land animal?", "options": ["Cheetah", "Lion", "Tiger", "Horse"], "answer": "Cheetah"},
    ],
    "Science": [
        {"question": "H2O is?", "options": ["Water", "Oxygen", "Hydrogen", "Salt"], "answer": "Water"},
        {"question": "Earth revolves around?", "options": ["Moon", "Mars", "Sun", "Venus"], "answer": "Sun"},
        {"question": "Plant food process?", "options": ["Respiration", "Photosynthesis", "Digestion", "Circulation"], "answer": "Photosynthesis"},
        {"question": "Force unit?", "options": ["Newton", "Joule", "Watt", "Volt"], "answer": "Newton"},
        {"question": "Human heart chambers?", "options": ["2", "3", "4", "5"], "answer": "4"},
    ]
}

# ---------- Session-state rerun helper ----------
if "rerun_trigger" not in st.session_state:
    st.session_state.rerun_trigger = False

def trigger_rerun():
    st.session_state.rerun_trigger = not st.session_state.rerun_trigger

# ---------- Layout ----------
st.set_page_config(page_title="Quiz Championship", layout="wide")

st.sidebar.title("📜 Quiz Rules")
st.sidebar.write("""
- Enter **Name & Email** to register    
- Choose a category or **All Subjects**    
- **10 seconds** per question    
- Scores saved to Google Sheets  
""")

# Checkbox to toggle chatbot
show_chatbot = st.sidebar.checkbox("🤖 Show AI Assistant", value=False)

# ---------- Player Registration ----------
if "user" not in st.session_state:
    st.session_state.user = None

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
            trigger_rerun()
        else:
            st.error("Please provide both Name and Email.")
    st.stop()

# ---------- Two-column layout ----------
col1, col2 = st.columns([2, 1])

with col1:
    st.title("🎯 Professional Quiz Championship")

    category = st.selectbox("Choose a Category", list(quiz_data.keys()) + ["All Subjects"])

    # Load questions
    if "questions" not in st.session_state or st.session_state.get("active_category") != category:
        if category == "All Subjects":
            all_q = []
            for v in quiz_data.values():
                all_q.extend(v)
            st.session_state.questions = random.sample(all_q, len(all_q))
        else:
            st.session_state.questions = random.sample(quiz_data[category], len(quiz_data[category]))
        st.session_state.active_category = category
        st.session_state.q_index = 0
        st.session_state.score = 0
        st.session_state.start_time = None

    questions = st.session_state.questions

    # Timer refresh
    st_autorefresh(interval=1000, key="quiz_refresh")

    if "feedback" in st.session_state and st.session_state.feedback:
        msg, type_ = st.session_state.feedback
        getattr(st, type_)(msg)
        st.session_state.feedback = None

    if st.session_state.q_index < len(questions):
        q = questions[st.session_state.q_index]
        st.subheader(f"Question {st.session_state.q_index + 1} of {len(questions)}")
        st.write(q["question"])

        if st.session_state.start_time is None:
            st.session_state.start_time = time.time()

        time_left = 10 - int(time.time() - st.session_state.start_time)
        st.markdown(f"**⏱ Time left:** {max(time_left, 0)} seconds")

        if time_left <= 0:
            st.session_state.feedback = ("⏰ Time’s up! No points awarded.", "error")
            st.session_state.q_index += 1
            st.session_state.start_time = None
            st.rerun()

        choice = st.radio("Options", q["options"], key=f"opt_{st.session_state.q_index}")

        if st.button("Submit Answer", key=f"submit_{st.session_state.q_index}"):
            elapsed = time.time() - st.session_state.start_time
            if elapsed > 10:
                st.session_state.feedback = ("⏰ Time’s up! No points awarded.", "error")
            elif choice == q["answer"]:
                st.session_state.feedback = ("✅ Correct!", "success")
                st.session_state.score += 1
            else:
                st.session_state.feedback = (f"❌ Wrong! Correct answer: {q['answer']}", "error")

            st.session_state.q_index += 1
            st.session_state.start_time = None
            st.rerun()

    else:
        st.success(f"🏆 Quiz Over! {st.session_state.user['name']}, score: {st.session_state.score}/{len(questions)}")

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

        worksheet = st.session_state.worksheet_cache or open_sheet("QuizResults")

        st.subheader("🏅 Top 5 Players")
        try:
            records = worksheet.get_all_records()
            if records:
                df = pd.DataFrame(records)
                if "Score" in df.columns:
                    df["Score"] = pd.to_numeric(df["Score"], errors="coerce").fillna(0).astype(int)
                    top5 = df.sort_values("Score", ascending=False).head(5)
                    st.table(top5[["Name", "Score", "Category"]])
                else:
                    st.write(df.head(5))
            else:
                st.write("No scores yet.")
        except Exception as e:
            st.error(f"Error loading leaderboard: {e}")

        if st.button("Play Again"):
            st.session_state.q_index = 0
            st.session_state.score = 0
            st.session_state.start_time = None
            st.session_state.score_saved = False
            st.session_state.feedback = None
            st.rerun()

# ---------- AI Assistant ----------
with col2:
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if show_chatbot:
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
