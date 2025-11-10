# The Overly Verbose GPA Calculator

## Description
This Python program helps students calculate their GPA on a 4.0 scale.  
It allows the user to:
- Enter and validate 5 grades  
- Calculate their current GPA  
- Compare performance between the first and second half of classes  
- Set a goal GPA and see if it’s achievable  

---

## Decision Tree
Start
│                                                                          
├─► Welcome message                                                             
│                                                                                       
├─► Input 5 grades (each 0.0–4.0)                                                              
│ └─ Validate each grade                                                        
│                                                                    
├─► Calculate current GPA                                                            
│                                                                                              
├─► Ask: Analyze "first" or "second" half?                                                
│ ├─ If first → use first half of grades                                            
│ └─ If second → use second half                                                
│                                                                
├─► Calculate semester GPA                                        
│ ├─ If higher → "Good job!"                                          
│ ├─ If lower → "Time to lock in!"                                                      
│ └─ If same → "Consistent work!"                                    
│                                                        
├─► Ask for goal GPA                                                                  
│ ├─ If goal ≤ current → "Already meets goal!"                                                        
│ └─ If goal > current → Check if achievable by raising one grade to 4.0                                  
│ ├─ If yes → Show which grade(s) to improve                                                
│ └─ If no → Suggest improving multiple grades                                                    
│                                                            
└─► End program with thank-you message                                            


---

## Example Run

welcome to The Overly Verbose GPA Calculator
Lets get started
Enter grade #1 (0.0-4.0): 3.7
Enter grade #2 (0.0-4.0): 3.0
Enter grade #3 (0.0-4.0): 2.8
Enter grade #4 (0.0-4.0): 3.9
Enter grade #5 (0.0-4.0): 3.5

All grades recorded: [3.7, 3.0, 2.8, 3.9, 3.5]

Calculating.. crunch
Your current GPA is: 3.38

Would you like to analyze your 'first' or 'second' half of classes second

Your second semester GPA is: 3.70
Good Job! You improved in this part of the semester.

What’s your goal GPA? 3.8

You can reach your goal of 3.80 by raising one grade to 4.0!
Try improving grade(s): 2, 3

Thanks for using The Overly Verbose GPA Calculator

---

## How to Run
1. Save the file as `gpa_calculator.py`  
2. Open a terminal or command prompt  
3. Run the program using:
4. Follow the on-screen instructions  

