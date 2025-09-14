import time
import json
import random
import sys

# ---- Quiz questions ----
questions = [
    {
        "question": "What is the capital of France?",
        "options": ["Paris", "Berlin", "Madrid", "Rome"],
        "answer": "Paris"
    },
    {
        "question": "Which planet is known as the Red Planet?",
        "options": ["Earth", "Mars", "Jupiter", "Saturn"],
        "answer": "Mars"
    },
    {
        "question": "Who wrote 'Hamlet'?",
        "options": ["Charles Dickens", "Leo Tolstoy", "William Shakespeare", "Mark Twain"],
        "answer": "William Shakespeare"
    },
    {
        "question": "Which is the fastest land animal?",
        "options": ["Leopard", "Horse", "Tiger", "Cheetah"],
        "answer": "Cheetah"
    },
    {
        "question": "Which gas do plants absorb from the atmosphere?",
        "options": ["Oxygen", "Carbon Dioxide", "Nitrogen", "Hydrogen"],
        "answer": "Carbon Dioxide"
    }
]

# ---- Scoreboard helpers ----
SCOREBOARD_FILE = "scoreboard.json"

def load_scoreboard():
    try:
        with open(SCOREBOARD_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_scoreboard(scoreboard):
    with open(SCOREBOARD_FILE, "w") as f:
        json.dump(scoreboard, f, indent=2)

# ---- Timed Input Helper (Fixed) ----
def timed_input(prompt, timeout=10):
    """
    Prompt user for input with timeout. Returns None if time runs out.
    Works on both Windows and Unix systems.
    """
    print(prompt, end='', flush=True)

    start_time = time.time()
    result = ""

    try:
        # Windows-specific method (msvcrt)
        import msvcrt
        while True:
            if msvcrt.kbhit():
                char = msvcrt.getwch()
                if char == '\r':  # Enter key
                    print()  # move to next line
                    return result
                elif char == '\b':  # Backspace
                    if result:
                        result = result[:-1]
                        sys.stdout.write('\b \b')
                        sys.stdout.flush()
                else:
                    result += char
                    sys.stdout.write(char)
                    sys.stdout.flush()

            if (time.time() - start_time) > timeout:
                print()  # move to next line
                return None
            time.sleep(0.05)

    except ImportError:
        # Unix / Mac (uses select)
        import select
        rlist, _, _ = select.select([sys.stdin], [], [], timeout)
        if rlist:
            return sys.stdin.readline().strip()
        else:
            return None

# ---- Main Quiz ----
def play_quiz():
    score = 0
    shuffled_questions = questions[:]  # Copy questions
    random.shuffle(shuffled_questions)

    for q in shuffled_questions:
        random.shuffle(q["options"])

        print("\n" + q["question"])
        for i, opt in enumerate(q["options"], start=1):
            print(f"{i}. {opt}")

        start_time = time.time()
        answer = timed_input("\nEnter option number (1-4) or 'q' to quit: ", timeout=10)
        elapsed_time = time.time() - start_time

        if answer is None:  # Timed out
            print("⏰ Time’s up! Moving to next question.")
            continue

        if answer.lower() == "q":
            print("Exiting quiz early.")
            break

        try:
            answer = int(answer)
        except ValueError:
            print("❌ Invalid input. Skipping question...")
            continue

        if 1 <= answer <= 4 and q["options"][answer - 1] == q["answer"]:
            print(f"✅ Correct! (⏱️ {elapsed_time:.2f} seconds)")
            score += 1
        else:
            print(f"❌ Wrong! The correct answer was {q['answer']}.")

    print(f"\n🎯 Your final score: {score}/{len(shuffled_questions)}")

    name = input("Enter your name for the scoreboard: ").strip()
    if not name:
        name = "Anonymous"

    scoreboard = load_scoreboard()
    scoreboard.append({"name": name, "score": score})
    save_scoreboard(scoreboard)

    top_players = sorted(scoreboard, key=lambda x: x["score"], reverse=True)[:3]
    print("\n🏆 Top Players:")
    for idx, player in enumerate(top_players, start=1):
        print(f"{idx}. {player['name']} - {player['score']}")

# ---- Replay Loop ----
while True:
    play_quiz()
    again = input("\nPlay again? (y/n): ").lower()
    if again != "y":
        print("Thanks for playing! 👋")
        break
