def cpystr(dest: char**, src: char**):
    len = strlen(*src)
    *dest = <char*>malloc(len + 1)
    strncpy(*dest, *src, len)
    (*dest)[len] = '\0'

class A:
    x = 0
    y: char*

    def print(self: A*):
        printf("A: %d, %s\n", self->x, self->y)

    def __init__(self: A*, x: int, name: char*):
        self->x = x 
        cpystr(&self->y, &name)

    def __del__(self: A*):
        free(self->y)


class Object:
    def print(self: Object*):
        printf("<Object at %p>\n", self)


#class Person(Object):
class Person:
    name: char* 

    def __init__(self: Person*, name: char*):
        cpystr(&self->name, &name)

    def __del__(self: Person*):
        free(self->name)

    def print(self: Person*):
        printf("%s is a Person\n", self->name)


def main():
    a = new_A(10, "something")
    A_print(a)
    del_A(a)

    o = new_Object()
    Object_print(o)
    del_Object(o)

    p = new_Person("Jon")
    Person_print(p)
    p->print()
    x = Person_print
    x(p)
    x = p->print 
    x(p)
    del_Person(p)

    return 0
