import random

#function to calculate grade
def get_grade(score, total):
    percentage = (score/total)*100
    if percentage >=90:
       grade = "A"
    elif percentage >=80:
      grade ="B"
    elif percentage >=50:
      grade = "C"
    else:
      grade = "fail"
    return percentage, grade      

#Question bank with categories
questions_bank = {
    "Math": [
        {"q":"What is 5 + 67?", "a":"72"},
        {"q":"What is 5 * 20?", "a":"100"},
        {"q":"What is 30 - 5?", "a":"25"},
        {"q":"What is 100 + 20 - 20?", "a":"100"},
    ],
    "Science": [
        {"q":"Which planet is red planet?",  "a":"mars"},
        {"q":"What do humans need to breathe?", "a":"oxygen"},
        {"q":"What organ pump blood in body?", "a":"heart"},
        {"q":"largest sea animal?","a":"whale"},
    ],
    "English": [
        {"q": "What is the opposite of hot?", "a": "cold"},
        {"q": "Which word is a noun: run, apple, quickly?", "a": "apple"},
        {"q": "What is the plural of child?", "a": "children"},
        {"q": "What is opposite of fast?", "a": "slow"}
    ]

}
     

print("Welcome to the Quiz Game! \n")
print("Choose a category: Math / Science / English")
category = input("Enter category:").title()

if category not in questions_bank:
    print("Invalid category!!! Exiting........")
else: 
    questions = questions_bank[category]    
    random.shuffle(questions)
 

    score=0
    for question in questions:
      answer = input(question["q"]+" ")
      if answer.lower()==question["a"]:
         print("correct\n")
         score+=1
      else:
         print("wrong\n")


percentage,grade = get_grade(score, len(questions))

print(f"Final score : {score}/{len(questions)}")
print(f"Percentage: {percentage:.2f}%")
print(f"Grade:{grade}")

