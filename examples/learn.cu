# Single-line comments start with #

"Strings can be used as comments"

"""
Multiline strings are 
made using triple quotes.
"""

# Contants can be defined with the define statement 
define DAYS_IN_YEAR 365

# The value following the define keyword can also be optional 
# and used by the C preprocessor
define MACRO_VARIABLE

# Enumerations can be defined as a list of keywords.
# Unlike C/C++ enums, default values cannot be set in these.
enum days {SUN, MON, TUE, WED, THU, FRI, SAT}

# Import local headers with include 
# NOTE: System level includes are not required because all functions, 
# variables, and types defined in the C standard headers are 
# treated as builtin functions.
include "myheader.hu"

# Function declarations are similar to function definitions in python,
# but with type annotations and no body.
# These should generally be declared in your header files.
def function_1() -> void 

# Function arguments can be specified with or without a type.
# NOTE: If a type is not specified, the type is inferred based on the types 
# of variables passed to this function as arguments when it is called.
def add_two_ints(x1: int, x2: int) -> int
def add_two_things(x1: int, x2: int) -> int

# NOTE: Functions that are declared without a type automatically default
# to int type, like C.
def func_no_specified_ret()

# The program's entry poiny is a function called "main"
# which can accept either no arguments, or 2 arguments, and 
# returns a string, similar to C.
def main(argc: int, argv: char[][]):
    # Also could have been declared as:
    # def main()
    # def main(argc, argv)  # type inference fills in the types

    pass  # Just a regular no-op 

    # printf() is the same as printf in c.
    # stdio.h does not have to be included b/c all functions defined 
    # in c standard headers are included as builtin functions.
    printf("%d\n", 0)

    """
    Types
    """

    # Variables can initially be declared with or without the type 
    x: int  # x declared as an int
    y: int = 4  # y declared as an int defaulted to 4
    z = 4  # First declaration of z, which is declared as the type of 
           # the right hand side of the assignment 

    # ints are Usually 4 bytes
    x_int: int 

    # shorts are usually 2 bytes 
    x_short: short 

    # chars are 1 byte 
    x_char: char = 0
    y_char = 'y'  # Char literals are quoted with single quotes
