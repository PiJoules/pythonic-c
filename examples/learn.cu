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
def demo_func_ptrs() -> void

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

    # Arrays are mutable 
    my_array[1] = 2 
    printf("%d\n", my_array[1])

    # Array sizes do not need to be declared at compile time. 
    # These are variable-lenght arrays.
    printf("Enter the array size: ")
    array_size: int 
    fscanf(stdin, "%d", &array_size)
    var_length_array: int[array_size]
    printf("sizeof(var_length_array) in bytes: %zu\n", sizeof(var_length_array))

    # Strings are arrays of chars terminated by a NULL character (0x00)
    # String literals already include the null character bu default.
    a_string = "This is a string"
    printf("%s\n", a_string)
    printf("%d\n", a_string[16])

    # Multidimensional arrays 
    multi_array = [
        [1, 2, 3, 4, 5],
        [6, 7, 8, 9, 10]
    ]

    # Access elements 
    array_int = multi_array[0][2]
    printf("%d\n", array_int)  # 3 
    assert(9 == multi_array[1][2] + 1)

    """
    Operators
    """

    # Arithmetic is straightforward
    # Testing using the assert function
    i1 = 1 
    i2 = 2 
    f1 = 1.0 
    f2 = 2.0 

    assert(i1 + i2 == 3)
    assert(i2 - i1 == 1)
    assert(i2 * i1 == 2)
    assert(i1 / i2 == 0)  # Floor/integer division 

    # You need to cast at least one integer to get a floating point result 
    # Casting is done with < and >
    x_cast1 = <float> i1 / i2
    printf("Should be 0.5: %f\n", x_cast1)  # 0.5
    printf("Should also be 0.5: %f\n", i1 / <double> i2)
    printf("Should also be 0.5: %f\n", f1 / f2)

    # Modulo exists as well
    assert(11 % 3 == 2)

    # Comparison operators return ints where 0 is trated as False 
    # and anything else is True
    assert((3 == 2) == 0)
    assert((3 != 2) == 1)
    assert(3 > 2)
    assert(not (3 < 2))
    assert(2 <= 2)
    assert(2 >= 2)

    # This is also not Python (yet...) - comparisons don't chain 
    # The line below evaluates to is treated as (7 > 6) > 5 
    # which simplifies to 1 > 5 which is False 
    a = 6 
    between_7_and_5 = 7 > a > 5
    assert(not between_7_and_5)

    # Instead chain using 'and'
    between_7_and_5 = 7 > a and a > 5
    assert(between_7_and_5)

    # Logic works on ints 
    assert(not 3 == 0)
    assert(not 0 == 1)
    assert(1 and 1)
    assert(not (0 and 1))
    assert(0 or 1)
    assert(not (0 or 0))

    # Increment and decrement operators
    j = 0 
    s = j++  # Return j THEN increase j
    assert(s == 0)
    assert(j == 1)

    s = --j  # Decrement j THEN return j 
    assert(s == 0)
    assert(j == 0)

    # Bitwise operators
    assert(~15 == -16)  # Bitwise negation/1's complement
    assert((2 & 3) == 2)  # Bitwise and 
    assert((2 | 3) == 3)  # Bitwise or
    assert((2 ^ 3) == 1)  # Bitwise xor 
    assert(1 << 1 == 2)  # Bitwise left shift 1
    assert(4 >> 1 == 2)  # Bitwise right shift 1 

    """
    Control flow
    """

    # If-elif-else ladder
    if 0:
        printf("I will never run\n")
    elif 0:
        printf("I will also never run\n")
    else:
        printf("This prints\n")

    # While loop
    ii = 0 
    while ii < 10:
        printf("%d, ", ii++)
    printf("\n")

    # Do-while loop 
    kk = 0 
    dowhile ++kk < 10:  # This gets executed after 1 cycle
        printf("%d, ", kk)
    printf("\n")

    # Switch statement 
    a = 3
    switch a:
        case 0:
            printf("a == 0\n")
            break 
        case 1:
            printf("a == 1\n")
            break 
        case 3, 4:
            printf("a is 3 or 4\n")
            break 
        else:
            fputs("Error\n", stderr)
            exit(-1)
            break 

    """
    Typecasting
    """

    # Cast to another type using < > (in C this is done with parenthesis)
    x_val = 1
    printf("%d\n", x_val)
    printf("%d\n", <short> x_val)
    printf("%d\n", <char> x_val)

    # Types will overflow without warning
    # char max == 255 if char is 8 bits long
    assert(<uchar> 257 == 1)

    # Integral types can be cast to floating point types and vice-versa
    printf("%f\n", <float>100)  # %f formats a float
    printf("%lf\n", <double>100)  # %lf formats a double
    printf("%d\n", <char>100.0)

    """
    Pointers
    """

    # A pointer is a variable declared to store a memory address. Its declaration will
    # also tell you the type of data it points to. You can retrieve the memory address
    # of your variables, then mess with them.

    x = 5
    printf("%p\n", <void[]>&x)  # Use & to retrieve the address of a variable 

    # Pointers are declared with empty brackets ([]),
    # similar to an array declaration, but without a size 
    px: int[] = &x
    not_a_pointer: int 
    printf("%p\n", <void[]> px)  # Print some address in memory
    printf("pointer size: %zu, int size: %zu\n", sizeof(px), sizeof(not_a_pointer))

    # To retrive the value at the address a pointer points to,
    # dereference it using '*'
    assert(*px == 5)

    # The pointer value can be changed 
    px_cpy = px
    (*px)++
    assert(*px == 6)
    assert(px == px_cpy)

    # Arrays allocate a continuous block of memory 
    x_array = [1, 2, 3, 4, 5]
    
    # Declare a pointer an initialize it to x_array 
    x_ptr = x_array 

    # x_ptr now points to the first element of x_array (1)
    assert(*x_ptr == 1)

    # Assign string 
    otherarr = "somestring"
    ptr = otherarr 
    printf("%s, %s\n", otherarr, ptr)

    # Pointers are incremented based on their type 
    assert(*(ptr + 1) == ptr[1])

    # You can dynamically allocate memory with malloc, which takes one 
    # argument of size_t representing the number of bytes to allocate.
    my_ptr = <int[]> malloc(sizeof(int) * 3)

    # Because malloc returns a void pointer, not specifying the type 
    # during initial assignment will cause my_ptr to be inferred as a 
    # void pointer. Casting it as an int pointer, or specifying the 
    # variable type creates a pointer of that type.
    # my_ptr: int[] = malloc(sizeof(int) * 3)  works also

    # Assign to malloc'd space
    my_ptr[0] = 1 
    my_ptr[1] = 2 
    my_ptr[2] = 3 
    assert(my_ptr[0] + my_ptr[1] == my_ptr[2])

    # Always remember to free malloc'd memory 
    free(my_ptr)

    # Call a function
    function_1()
    demo_func_ptrs()

    # End of main function 


# Function definition 
# Essentially the same as a declaration, but it has a body. 
# If the function type was declared before, the return type 
# and argument types match it, so it does not need to be 
# specifed again.
def add_two_ints(x1, x2):
    return x1 + x2 


# Function definition for a function that was not previously
# declared must specify argument types and return types, though
# if a return type is not specified, int is the default return type
def add_two_ints_plus_1(x1: int, x2: int) -> int:
    return x1 + x2 + 1


"""
User defined types and structs
"""

# Typedefs can be used to create type aliases 
typedef int my_type 
my_type_var: my_type = 0 

# Structs are collections of data where the members are allocated
# sequentially in the order they are written.
struct rectangle {
    width: uint,
    height: uint,
}


def function_1():
    # Newly defined structs are type'd as their name.
    # You do not type 'struct rectangle', just 'rectangle'
    my_rect: rectangle

    # Access struct members with '.'
    my_rect.width = 10 
    my_rect.height = 20 

    # Declare pointers to structs 
    my_rect_ptr = &my_rect 

    # Use derefencing to set sruct pointer members 
    (*my_rect_ptr).width = 30
    assert(my_rect.width == 30)

    # Alternatively use the -> shorthand for the sake of readability
    my_rect_ptr->width = 15
    assert(my_rect.width == 15)
    assert(my_rect_ptr->width == my_rect.width)


"""
Function pointers
"""

# Functions are also types and can be stored as variables like so 

def demo_func_ptrs():
    # Declare adder_func as a function which takes 2 ints and returns an int
    adder_func: (int, int) -> int
    adder_func = add_two_ints 

    # The type declaration above the assignment is unecessary since 
    # type inference would infer addr_func as the proper func type 
    # during assignment 
    assert(adder_func(1, 2) == 3)
    assert(adder_func(3, 0) == adder_func(1, 2))

    # New function assignment 
    adder_func = add_two_ints_plus_1
    assert(adder_func(1, 2) == 4)
