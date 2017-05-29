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

    # chars are 1 byte 
    x_char: char = 0
    y_char = 'y'  # Char literals are quoted with single quotes

    # shorts are usually 2 bytes 
    x_short: short 

    # ints are usually 4 bytes
    x_int: int 

    # longs are compiled to long longs in C and usually about 64 bits 
    x_long: long 

    # The previous types are all signed.
    # Unsigned versions of the previously mentioned types start with a 'u'
    x_uint: uint 

    # floats are usually 32-bit floating point numbers
    x_float: float = 0.0

    # doubles are usually 64-bit floating point numbers
    x_double: double = 0.0

    # The sizeof function will give you the the size of a variable or type
    # in bytes. Only the function is available, not the sizeof statement.
    int_size = sizeof(int)
    large_num_size = sizeof(9223372036854775807)  # 2^63
    printf("sizeof(int): %zu\n", int_size)
    printf("sizeof(2^63): %zu\n", large_num_size)

    # Just like in C, if the sizeof function is called on an expression,
    # that expression is not evaluated.
    a = 1 
    printf("original value of a: %d\n", a)
    size = sizeof(a++)
    printf("sizeof(a++) = %zu where new value of a = %d\n", size, a)

    # Arrays must be initialized using a concrete size 
    my_char_array: char[20]  # This array occupies 20 bytes
    my_int_array: int[20]  # This array occupies 80 bytes

    # You can initialize an array to all zeros thusly
    my_array: char[20] = [0]

    # If the type is not specified for an array literal,
    # it defaults to an int array of the literal's size
    my_array_default = [1, 2, 3]  # int array of size 3

    # Index an array just like any language 
    my_array[0]
