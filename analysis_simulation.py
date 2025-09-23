# Online Python - IDE, Editor, Compiler, Interpreter

import math
import random


A= 10 #100 # Amortized investment
R= 10 #0.83 #%
CI=0 # total current investment
TOTAL_ITER=5 # total iterations
FIXED_CAPITAL= 1000 #1000 # current money at hand

def depreciate(stop=1, rate=R, A=100, CI=0, fixed_capital=1000 ):
    ''' Depreciate the current investment CI by rate R% for stop iterations
        Every time the investment depreciates, invest A amount from fixed capital
        If fixed capital is less than A, stop investing
    '''
    print("***********************Depreciate***********************")
    if fixed_capital<A:
        print("Not enough fixed capital to invest")
        return (CI, fixed_capital)
    ans=0
    for i in range(1,stop+1):
        if(fixed_capital<A):
            break
        else:
            fixed_capital-=A # invest A every decrease in rate R
        
        ans=CI
        for j in range(1,i+1):
            ans+=(pow((100-rate),j-1)/pow(100,j-1))*A
        print(ans)
    print("Initial CI:", ans , "Initial Fixed Capital:", fixed_capital)
    return (round(ans,4), round(fixed_capital,4)) # return current investment and remaining fixed capital
    



def appreciate(stop=1, rate=R, A=100, CI=0, fixed_capital=1000):
    ''' 
        Appreciate the current investment CI by rate R% for stop iterations
        Every time the investment appreciates, recover A amount to fixed capital
        If CI is less than A, stop recovering
    '''
    print("***********************APPRECIATE***********************")
    ans=CI
    for i in range(1,stop+1):
        print(ans)
        # for j in range(1,i+1):
        ans=((1+rate/100))*ans
        if(ans>A):
            ans-=A  
            fixed_capital+=A # recover A every increase in rate R
        else:
            break
    CI=ans
    print("Initial CI:", CI , "Initial Fixed Capital:", fixed_capital)
    return (round(ans,4), round(fixed_capital,4)) # return current investment and remaining fixed capital
        


# Simulate btcusdt price from historical data
#



# CI=0
# COUNTER=0
# FixedCapital=40
# while(True):
#     # generate random number
#     rand_num = random.randint(0, 20)
#     COUNTER+=1
#     print(rand_num)
#     if rand_num%2==0:
#         CI, FixedCapital = depreciate(stop=TOTAL_ITER, fixed_capital=FIXED_CAPITAL, A=A, CI=CI )
#     else:
#         CI, FixedCapital = appreciate(stop=TOTAL_ITER, A=A, CI=CI, fixed_capital=FIXED_CAPITAL)
#     if(COUNTER==10):
#         break