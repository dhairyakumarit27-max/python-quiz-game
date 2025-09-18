import streamlit as st
import random
import time
import json
import gspread
import pandas as pd
from gspread.exceptions import SpreadsheetNotFound
from google.oauth2.service_account import Credentials
from ai_utils import generate_questions, ask_ai


# ---------- QUIZ UI SETUP + THEME ----------
def apply_custom_theme():
    st.markdown(
        """
        <style>
        /* General app styling */
        body, .stApp {
            background-color: #FFFFFF; /* White background */
            color: #000000;            /* Black text */
        }

        /* Standard buttons (Next, Submit) */
        .stButton>button {
            background-color: #4B9CD3; /* Blue button */
            color: #FFFFFF;            /* White button text */
            border-radius: 8px;
            border: none;
            padding: 0.5em 1em;
            font-weight: bold;
        }
        .stButton>button:hover {
            background-color: #357ABD; /* Darker blue on hover */
        }

        /* Quiz option cards */
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

# Apply theme
apply_custom_theme()

# ---------- QUIZ UI SETUP ----------

st.title("🧠 Fun Quiz Game")



# ---------- Google Sheets client helper ----------
def get_gspread_client():
    """
    Returns a gspread client using Streamlit secrets.
    """
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client

# ---------- Groq client helper ----------
from groq import Groq
import streamlit as st

@st.cache_resource
def get_groq_client():
    """
    Returns a Groq client using the API key from Streamlit secrets.
    """
    api_key = st.secrets.get("GROQ_API_KEY")
    if not api_key:
        st.error("Groq API key not found in secrets.toml")
        st.stop()
    return Groq(api_key=api_key)


# ---------- Open sheet and ensure headers ----------
def open_sheet(sheet_name="QuizResults"):
    client = get_gspread_client()
    try:
        sh = client.open(sheet_name)
    except SpreadsheetNotFound:
        st.error(f"Spreadsheet '{sheet_name}' not found. Create it and share with the service account email.")
        st.stop()
    worksheet = sh.sheet1
    return worksheet

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

# ---------- UI / App ----------
st.set_page_config(page_title="Quiz Championship", layout="centered")
st.sidebar.title("📜 Quiz Rules")
st.sidebar.write("""
- Enter **Name & Email** to register  
- Choose a category or **All Subjects**  
- **10 seconds** allowed per question (time checked at submission)  
- Scores are saved to Google Sheets and top 5 leaderboard shown
""")

# Registration
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

# User registered
st.title("🎯 Professional Quiz Championship")
category = st.selectbox("Choose a Category", list(quiz_data.keys()) + ["All Subjects"])

# Prepare questions for chosen category
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

# ---------- Show question or final screen ----------
from streamlit_autorefresh import st_autorefresh

# Auto-refresh every 1 second (for timer countdown)
st_autorefresh(interval=1000, key="quiz_refresh")

# Show feedback message if exists
if "feedback" in st.session_state and st.session_state.feedback:
    msg, type_ = st.session_state.feedback
    if type_ == "success":
        st.success(msg)
    elif type_ == "error":
        st.error(msg)
    elif type_ == "info":
        st.info(msg)
    st.session_state.feedback = None  # clear after showing

if st.session_state.q_index < len(questions):
    q = questions[st.session_state.q_index]
    st.subheader(f"Question {st.session_state.q_index + 1} of {len(questions)}")
    st.write(q["question"])

    # Start timer if not set
    if st.session_state.start_time is None:
        st.session_state.start_time = time.time()

    # Countdown
    time_left = 10 - int(time.time() - st.session_state.start_time)
    st.markdown(f"**⏱ Time left:** {max(time_left, 0)} seconds")

    # If time runs out
    if time_left <= 0:
        st.session_state.feedback = ("⏰ Time’s up! No points awarded.", "error")
        st.session_state.q_index += 1
        st.session_state.start_time = None
        st.rerun()

    # Show options
    choice = st.radio("Options", q["options"], key=f"opt_{st.session_state.q_index}")

    # Submit answer button
    if st.button("Submit Answer", key=f"submit_{st.session_state.q_index}"):
        elapsed = time.time() - st.session_state.start_time
        if elapsed > 10:
            st.session_state.feedback = ("⏰ Time’s up! No points awarded.", "error")
        elif choice == q["answer"]:
            st.session_state.feedback = ("✅ Correct!", "success")
            st.session_state.score += 1
        else:
            st.session_state.feedback = (f"❌ Wrong! Correct answer: {q['answer']}", "error")

        # Move to next question
        st.session_state.q_index += 1
        st.session_state.start_time = None
        st.rerun()

else:
    # Quiz finished
    st.success(f"🏆 Quiz Over! {st.session_state.user['name']}, "
               f"your score: {st.session_state.score}/{len(questions)}")

    # Save score only once
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

    # Use cached worksheet for leaderboard
    worksheet = st.session_state.worksheet_cache or open_sheet("QuizResults")

    # Show leaderboard
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

    # Restart button
    if st.button("Play Again"):
        st.session_state.q_index = 0
        st.session_state.score = 0
        st.session_state.start_time = None
        st.session_state.score_saved = False
        st.session_state.feedback = None
        st.rerun()
    
# ---------- AI Tools Section ----------

st.sidebar.markdown("---")
menu = ["Quiz", "AI Tools"]
choice = st.sidebar.selectbox("Menu", menu, index=0)  # Default = Quiz

if choice == "AI Tools":
    st.header("🤖 AI Tools")

    tab1, tab2 = st.tabs(["📘 Generate Questions", "💬 Chat Assistant"])

    # --- Question Generator ---
    with tab1:
        st.subheader("Generate Quiz Questions from Text")
        text_input = st.text_area("Paste text here:")
        num_q = st.slider("Number of questions", 1, 10, 5)
        if st.button("Generate Questions"):
            if text_input.strip():
                with st.spinner("AI is generating questions..."):
                    output = generate_questions(text_input, num_q)
                st.code(output, language="json")
            else:
                st.warning("Please paste some text.")

    # --- Chat Assistant ---
    with tab2:
        st.subheader("Chat with AI Assistant")
        user_q = st.text_input("Ask me anything:")
        if st.button("Ask AI"):
            if user_q.strip():
                with st.spinner("Thinking..."):
                    answer = ask_ai(user_q)
                st.success(answer)
            else:
                st.warning("Please type a question.")
