includel "ll.hu" 


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

    x = list_pop(lst)
    printf("Popped from list: %d\n", x)
    printf("list: ")
    print_list(lst)
    assert(not lst->length)

    del_list(lst)

    return 0
