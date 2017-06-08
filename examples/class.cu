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

    # Save each method in a container in the inferer to indicate these can be bounded methods.
    # When nodes of these types are inferred. Create, add, and return an altered Callable type 
    # that contains a reference to the instance.

    # Go back up to check call and infer the type of the func (which was replaced with the altered
    # Name) and infer this name as a new Callable type with an attribute that contains this name node 
    # also. When you check a Call whose func is of this callable type. Immediately prepend the node 
    # as the first argument.
    p->print()

    # x is now of the new callable type holding a reference to node Name("p").
    x = p->print  

    # Check the func and see it's just a name, but when the type is inferred, it is seen as the 
    # callable holding Name("p"). Prependt this node to the arg list.
    x()
#
#    # Infer the RHS type as the altered callable which stores Name("p")
#    x = (*p).print 
#    x(p)

    del_Person(p)

    return 0
