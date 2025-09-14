#program1 if,else
marks = int(input("Enter your marks:"))

if marks >= 40:
    print("you pass")
else:
      print("loser")


#program2 for
for i in range(1,6):
    print("hello",i, "baar")

#program3 while
count=3
while count>0:
    print("countdown:",count)
    count-=1



#mini quiz



score=0
print("welcome to quiz game")

#quetion1
answer = input("what is the capital of india?:")
if answer.lower()== "dehli":
    print("correct")
    score += 1
else:
    print("wrong")

#question2
answer = input("What is 5+55:")
if answer.lower()=="60":
    print("correct")
    score += 1
else:
    print("wrong")

#question#3
answer = input("what is the capital of rajasthan?:")   
if answer.lower()=="jaipur":
    print("correct")
    score += 1
else:
    print("wrong")
    

print(f"your final score is {score}/3")