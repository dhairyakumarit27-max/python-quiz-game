import streamlit as st
import random
import time
import json
import gspread
import pandas as pd
from gspread.exceptions import SpreadsheetNotFound
from google.oauth2.service_account import Credentials

# --------- DEBUGGING SNIPPET ---------
try:
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)

    st.write("✅ Service account connected!")
    st.write("📂 Available Sheets:", client.list_spreadsheet_files())

except Exception as e:
    st.error(f"❌ Error while testing Google Sheets access: {e}")
# --------------------------------------



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

# Show question or final screen
if st.session_state.q_index < len(questions):
    q = questions[st.session_state.q_index]
    st.subheader(f"Question {st.session_state.q_index + 1} of {len(questions)}")
    st.write(q["question"])

    # set start_time if not set
    if st.session_state.start_time is None:
        st.session_state.start_time = time.time()

    # visible countdown
    time_left = 10 - int(time.time() - st.session_state.start_time)
    st.markdown(f"**⏱ Time left:** {max(time_left,0)} seconds")

    choice = st.radio("Options", q["options"], key=f"opt_{st.session_state.q_index}")

    if st.button("Submit Answer"):
        elapsed = time.time() - st.session_state.start_time
        if elapsed > 10:
            st.error("⏰ Time’s up! No points awarded.")
        elif choice == q["answer"]:
            st.success(f"✅ Correct! ({elapsed:.1f}s)")
            st.session_state.score += 1
        else:
            st.error(f"❌ Wrong! Correct answer: {q['answer']}")

        st.session_state.q_index += 1
        st.session_state.start_time = None
        trigger_rerun()

else:
    st.success(f"🏆 Quiz Over! {st.session_state.user['name']}, your score: {st.session_state.score}/{len(questions)}")

    # Save to Google Sheets
    worksheet = open_sheet("QuizResults")
    ensure_headers(worksheet)
    worksheet.append_row([st.session_state.user["name"],
                          st.session_state.user["email"],
                          st.session_state.active_category,
                          st.session_state.score],
                         value_input_option="USER_ENTERED")

    # Show leaderboard (Top 5)
    st.subheader("🏅 Top 5 Players")
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

    if st.button("Play Again"):
        st.session_state.q_index = 0
        st.session_state.score = 0
        st.session_state.start_time = None
        trigger_rerun()
