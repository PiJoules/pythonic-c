includel "ll.hcu" 
include "assert.hcu"
include "stdio.hcu"


def main():
    lst = new_list()

    assert(not lst->length)
    printf("Empty list: ")
    print_list(lst)

    del_list(lst)


    lst = new_list()

    list_prepend(lst, 10)
    printf("List of size 1: ")
    print_list(lst)
    assert(lst->length == 1)

    del_list(lst)

    return 0
