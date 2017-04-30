# Comment

'single quote comment'
"double quote comment"

"""
multiline
double
quotes
"""

'''multiline
    single quotes'''

define CONSTANT
define DAYS_IN_A_YEAR 365

include "stdio.h"  # standard header include
includeloc "myheader.h"  # local header include


# Variable declaration
x: int
x: int[3]  # int array of size 3
x: int[]  # Generic int pointer (int*)
x: int[2][3]  # 2x3 array of ints

"""
# Variable declarations
x: int[][]  # double int pointer (int**)
x: int[3][]  # int *x[3]; x is an array of size 3 containg int pointers
             # x[0] gets the first int pointer, x[0][0] gets the first int in
             # the first int pointer
x: int[][3]  # int (*x)[3]; x is a pointer to an array of 3 ints
x: int[][3][]  # x is a pointer to an array of size 3 that contains pointers to ints

# Function declaration
def func() -> int[]  # int *x(); x is a function that returns int pointers
func: () -> int[]  # Alternative declaration

# Combinations
x: ((int) -> int)[3]  # x is an array of size 3 containg functions that takes an
                      # int and returns an int


# The following 3 are equivalent
x: (int) -> (float) -> (str)  # x is a function that takes an int which returns
                              # a function that takes a float which returns a
                              # str
x: (int) -> ((float) -> str)
def x(a: int) -> ((float) -> str)

# x is a function that returns a str and takes a function that returns a float
# and takes an int
x: ((int) -> float) -> str
"""


# Function declaration
def func()
def func() -> None  # Func decl with optional return type
def func(a, b) -> int


# Function definition
def func():
    x = 1
    print(x)
