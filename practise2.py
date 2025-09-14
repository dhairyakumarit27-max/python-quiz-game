import random

score = 0

questions = [
    {"q": "what is capital of india?", "a": "delhi"},
    {"q":" what is the date of christmas?", "a": "25 december"},
    {"q":"what is national game of india?", "a": "hockey"},
    {"q": "how many days in week?", "a": "7"},
]



#not a main code, just extra
name= input("enter your name:")
print("welcome to the quiz game",name, "happy journey")

open = input( "press any key to begin:")
print(" you time start now")




#main code start
#shuffle the questions list
random.shuffle(questions)

for question in questions:
    answer = input(question["q"]+" ")
    if answer.lower()==question["a"]:
      print("correct")
      score+=1
    else:
      print("wrong")

print(f"your final score is {score}/{len(questions)}")

