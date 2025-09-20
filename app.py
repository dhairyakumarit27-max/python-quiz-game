import streamlit as st
import random
import time
import json
import gspread
from google.oauth2.service_account import Credentials
from groq import Groq
from datetime import datetime

# ==============================
# Google Sheets Setup (robust)
# ==============================
def get_gspread_client():
    """
    Create a gspread client from service account JSON stored in Streamlit secrets.
    Expects st.secrets["GOOGLE_CREDENTIALS"] to be a JSON string.
    Expects optional st.secrets["GSHEET_NAME"] for the spreadsheet file name.
    """
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds)

def open_sheet(worksheet_name="Leaderboard"):
    """
    Open the Spreadsheet workbook named by st.secrets["GSHEET_NAME"] (fallback "QuizAppDB"),
    then return a worksheet object for worksheet_name. If that worksheet doesn't exist,
    create it and add a header row ["Name","Score","Timestamp"].
    This prevents WorksheetNotFound errors.
    """
    client = get_gspread_client()
    workbook_name = st.secrets.get("GSHEET_NAME", "QuizAppDB")
    try:
        book = client.open(workbook_name)
    except Exception as e:
        # Try creating the spreadsheet (may require Drive API permissions)
        # If creation fails, raise a helpful error.
        try:
            book = client.create(workbook_name)
        except Exception as ce:
            raise RuntimeError(
                f"Unable to open or create workbook '{workbook_name}'. "
                f"Original error: {e}. Create the spreadsheet manually or check service account permissions."
            ) from ce

    # Try to get the worksheet, else create it with a header row
    try:
        worksheet = book.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = book.add_worksheet(title=worksheet_name, rows="100", cols="10")
        # Add header row so get_all_records() returns dicts with keys
        worksheet.append_row(["Name", "Score", "Timestamp"])
    return worksheet

def save_result(name, score):
    """
    Append a result row to the leaderboard worksheet.
    Ensures header exists and then appends Name, Score, Timestamp.
    """
    worksheet = open_sheet("Leaderboard")
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    worksheet.append_row([name, int(score), timestamp])

def load_leaderboard(limit=50):
    """
    Load leaderboard records as list of dicts and sort by 'Score' (descending).
    Returns top `limit` rows.
    """
    worksheet = open_sheet("Leaderboard")
    data = worksheet.get_all_records()  # requires header row: Name, Score, Timestamp
    # Defensive: if 'Score' not present, return empty list
    if not data:
        return []
    if "Score" not in data[0]:
        return []
    try:
        return sorted(data, key=lambda x: int(x.get("Score", 0)), reverse=True)[:limit]
    except Exception:
        # In case Score can't be converted to int for some rows
        return sorted(data, key=lambda x: float(x.get("Score", 0) or 0), reverse=True)[:limit]

# ==============================
# Quiz Questions (5 each)
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

    if not st.session_state.registered:
        st.subheader("📝 Register to Start Quiz")
        name = st.text_input("Enter your name:", key="reg_name")
        category = st.selectbox("Choose Category", ["Maths", "Science"], key="reg_cat")
        if st.button("Start Quiz"):
            if name.strip():
                st.session_state.name = name.strip()
                st.session_state.category = category
                # store 5 random questions for this session
                st.session_state.questions = random.sample(QUIZ_QUESTIONS[category], 5)
                st.session_state.q_index = 0
                st.session_state.score = 0
                st.session_state.start_time = None
                st.session_state.feedback = None
                st.session_state.registered = True
                # ensure leaderboard worksheet exists early
                try:
                    open_sheet("Leaderboard")
                except Exception as e:
                    st.error(f"Warning: couldn't ensure leaderboard exists: {e}")
                st.experimental_rerun()
            else:
                st.warning("Please enter your name to continue.")
        return

    # --- Quiz Finished ---
    if st.session_state.q_index >= len(st.session_state.questions):
        st.success(f"🎉 Quiz finished! Your score: {st.session_state.score}/{len(st.session_state.questions)}")

        # Save result (wrapped in try/except to avoid crashing the app if Sheets fail)
        try:
            save_result(st.session_state.name, st.session_state.score)
        except Exception as e:
            st.error(f"Could not save score to leaderboard: {e}")

        st.header("🏆 Leaderboard (Top 5)")
        try:
            leaderboard = load_leaderboard()
            if leaderboard:
                st.table(leaderboard[:5])
            else:
                st.info("Leaderboard is empty.")
        except Exception as e:
            st.error(f"Error loading leaderboard: {e}")
        # Offer restart
        if st.button("Play Again"):
            # reset registration to allow new run
            st.session_state.registered = False
            st.experimental_rerun()
        return

    # --- Current Question ---
    q = st.session_state.questions[st.session_state.q_index]

    # Initialize timer for this question
    if st.session_state.get("start_time") is None:
        st.session_state.start_time = time.time()
        # clear any previous selected option for radio by re-creating key
        # Note: radio's key uses question index, so it's unique per question

    # Remaining time calculation
    elapsed = int(time.time() - st.session_state.start_time)
    remaining = max(0, 10 - elapsed)

    # Display time in a visually stable place
    timer_placeholder = st.empty()
    timer_placeholder.write(f"⏳ Time left: {remaining} sec")

    # Auto-move when time up (and avoid double increment)
    if remaining <= 0 and not st.session_state.get("feedback"):
        st.session_state.feedback = "⏰ Time’s up! No points awarded."
        st.session_state.q_index += 1
        st.session_state.start_time = None
        # immediate rerun so the UI updates to next question
        st.experimental_rerun()

    # Auto-refresh the page roughly every second so timer updates without clicks.
    # This uses Streamlit's query-params hack to trigger a rerun each second while
    # the question is active and time remains.
    # NOTE: This is a lightweight autorefresh — it updates the page every second only during an active question.
    if remaining > 0:
        params = st.experimental_get_query_params()
        now_sec = str(int(time.time()))
        # Only set and rerun if the last refresh param isn't the current second,
        # this prevents infinite immediate reruns inside the same second.
        if params.get("refresh") != [now_sec]:
            # Preserve any other params (not necessary here, but safe)
            st.experimental_set_query_params(refresh=now_sec)
            st.experimental_rerun()

    st.subheader(f"Question {st.session_state.q_index + 1}")
    st.write(q["question"])
    # radio with a stable key per question index to preserve user selection if rerun happens
    choice = st.radio("Options:", q["options"], key=f"q{st.session_state.q_index}")

    # Submit button: process answer and advance
    if st.button("Submit Answer", key=f"submit_{st.session_state.q_index}"):
        # Evaluate
        if choice == q["answer"]:
            st.session_state.score += 1
            st.session_state.feedback = "✅ Correct!"
        else:
            st.session_state.feedback = f"❌ Wrong! Correct answer: {q['answer']}"
        st.session_state.q_index += 1
        st.session_state.start_time = None
        # Let the UI update to next question immediately
        st.experimental_rerun()

    # Show feedback (if any) below the question
    if st.session_state.get("feedback"):
        st.info(st.session_state.feedback)
        # Clear feedback so it doesn't persist into the next question render
        st.session_state.feedback = None

# ==============================
# Streamlit Layout
# ==============================
st.set_page_config(layout="wide")

# Sidebar Rules
st.sidebar.title("📘 Rules")
st.sidebar.markdown("""
- You have **10 seconds** for each question.  
- Once you submit, the answer is final.  
- Score is saved to the leaderboard after the quiz.  
- Be honest & have fun! 🎉
""")

col1, col2 = st.columns([2, 1])  # 2/3 quiz, 1/3 AI

with col1:
    st.title("🎯 School Quiz Game")
    try:
        run_quiz()
    except Exception as e:
        # Catch-all to avoid crashing the app UI — show helpful message for debugging
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

    # Display chat history (most recent first)
    for chat in reversed(st.session_state.chat_history):
        st.markdown(f"**You:** {chat['user']}")
        st.markdown(f"**AI:** {chat['ai']}")
