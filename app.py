import streamlit as st
import random
import time
import json
import gspread
from google.oauth2.service_account import Credentials
from groq import Groq

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

def open_sheet(sheet_name):
    client = get_gspread_client()
    sheet = client.open("QuizAppDB")  # replace with your sheet name
    return sheet.worksheet(sheet_name)

def save_result(name, score):
    worksheet = open_sheet("QuizResults")
    worksheet.append_row([name, score])

def load_leaderboard():
    worksheet = open_sheet("QuizResults")
    data = worksheet.get_all_records()
    return sorted(data, key=lambda x: x["Score"], reverse=True)

# ==============================
# Quiz Questions
# ==============================
QUIZ_QUESTIONS = {
    "Maths": [
        {"question": "5 + 3 = ?", "options": ["6", "7", "8", "9"], "answer": "8"},
        {"question": "12 ÷ 4 = ?", "options": ["2", "3", "4", "6"], "answer": "3"},
    ],
    "Science": [
        {"question": "What planet is known as the Red Planet?", 
         "options": ["Earth", "Mars", "Jupiter", "Venus"], "answer": "Mars"},
        {"question": "Which gas do humans need to breathe?", 
         "options": ["Oxygen", "Carbon Dioxide", "Nitrogen", "Helium"], "answer": "Oxygen"},
    ]
}

# Make sure total = 7
ALL_QUESTIONS = (QUIZ_QUESTIONS["Maths"] + QUIZ_QUESTIONS["Science"]) * 2
ALL_QUESTIONS = ALL_QUESTIONS[:7]

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
        model="llama-3.1-8b-instant",  # ✅ updated model
        messages=messages,
    )
    return response.choices[0].message.content

# ==============================
# Quiz Logic
# ==============================
def run_quiz():
    # Registration
    if "registered" not in st.session_state:
        st.session_state.registered = False

    if not st.session_state.registered:
        st.subheader("📝 Register to Start Quiz")
        name = st.text_input("Enter your name:")
        category = st.selectbox("Choose Category", ["Maths", "Science"])
        if st.button("Start Quiz"):
            if name.strip():
                st.session_state.name = name
                st.session_state.category = category
                st.session_state.questions = random.sample(
                    QUIZ_QUESTIONS[category], min(2, len(QUIZ_QUESTIONS[category]))
                ) + random.sample(ALL_QUESTIONS, 5)  # total 7
                random.shuffle(st.session_state.questions)
                st.session_state.q_index = 0
                st.session_state.score = 0
                st.session_state.start_time = None
                st.session_state.feedback = None
                st.session_state.registered = True
                st.rerun()
            else:
                st.warning("Please enter your name to continue.")
        return

    # Quiz running
    if st.session_state.q_index >= len(st.session_state.questions):
        st.success(f"🎉 Quiz finished! Your score: {st.session_state.score}/{len(st.session_state.questions)}")
        save_result(st.session_state.name, st.session_state.score)

        st.header("🏆 Leaderboard")
        try:
            leaderboard = load_leaderboard()
            st.table(leaderboard[:5])
        except Exception as e:
            st.error(f"Error loading leaderboard: {e}")
        return

    q = st.session_state.questions[st.session_state.q_index]

    # Timer
    if st.session_state.start_time is None:
        st.session_state.start_time = time.time()
    elapsed = int(time.time() - st.session_state.start_time)
    remaining = max(0, 10 - elapsed)
    st.progress(remaining / 10)
    st.write(f"⏳ Time left: {remaining} sec")

    if remaining <= 0 and not st.session_state.feedback:
        st.session_state.feedback = "⏰ Time’s up! No points awarded."
        st.session_state.q_index += 1
        st.session_state.start_time = None
        st.rerun()

    # Question display
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

    # Feedback
    if st.session_state.feedback:
        st.info(st.session_state.feedback)
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
    run_quiz()

with col2:
    st.title("🤖 AI Assistant")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    user_input = st.text_input("Ask me anything:", key="chat_input")
    if st.button("Send"):
        if user_input:
            ai_reply = chat_with_ai(user_input, st.session_state.chat_history)
            st.session_state.chat_history.append({"user": user_input, "ai": ai_reply})

    # Display in reverse (latest first)
    for chat in reversed(st.session_state.chat_history):
        st.markdown(f"**You:** {chat['user']}")
        st.markdown(f"**AI:** {chat['ai']}")
