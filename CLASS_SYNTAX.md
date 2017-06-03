# Class syntax 
#
# Generics will be declared in optional brackets immediately
# following the class name. This is then followed by a list of 
# the parent classes stored in parenthesis.
#
# This new generic syntax is treated as a new type declaration.
#
# Both the generics in the brackets and in the parenthesis are 
# type declarations.
#
# Self is automatically inferred.
#
# Properties can either be declared in the class outside a method 
# or in any of the methods by explicitely dereferencing it. In this 
# case, the type is inferred.

class ArrayList[T](List[T]):
    buffer: T* = NULL 

    def __init__(self) -> void:
        self->length = 0
        ...

    def append(self, x: T) -> void:
        ... 

    def insert(self, i: size_t, x: T) -> void:
        ...

    def pop(self, i: size_t) -> T:
        ...

    def print(self) -> void:
        ...


# C translation 
#
# Curly brackets {} indicate to replace the contents with a previously 
# declared generic type.

# Arraylist_{T}.h 

typedef struct Arraylist_{T}_Parents Arraylist_{T}_Parents;
struct Arraylist_{T}_Parents {
};

typedef struct ArrayList_{T} ArrayList_{T};
struct ArrayList_{T} {
    

    void (*__init__)(Arraylist_{T} self);
    void (*append)(Arraylist_{T} self, {T} x);
    void (*insert)(Arraylist_{T} self, unsigned int i, {T} x);
    {T} (*pop)(Arraylist_{T} self, unsigned int i);
    void (*print)(Arraylist_{T} self);
};

# ArrayList_{T}.hu 

ifndef _ARRAYLIST_{T}_H
define _ARRAYLIST_{T}_H

struct Arraylist_{T} {
    __init__: (Arraylist_{T}) -> void,
    append: (Arraylist_{T}, {T}) -> void,
    insert: (Arraylist_{T}, size_t, {T}) -> void,
    pop: (Arraylist_{T}, size_t) -> {T},
    print: (Arraylist_{T}) -> void,
}

# Create the list 
Arraylist_{T}


endif


