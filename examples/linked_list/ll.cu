includel "ll.hcu"
include "stdio.hcu"


def new_list():
    lst = (List[])malloc(sizeof(List))
    lst->head = NULL
    lst->length = 0
    return lst


def del_list(l):
    while l->head != NULL:
        next_head = l->head->next
        free(l->head)
        l->head = next_head
    free(l)


def list_prepend(l, i):
    node = (Node[])malloc(sizeof(Node))
    node->value = i 
    node->next = l->head 
    l->head = node
    l->length++


def print_list(lst):
    printf("[")

    node = lst->head
    if node:
        printf("%d", node->value)
        node = node->next 

    while node:
        printf(", %d", node->value)
        node = node->next 

    printf("]\n")
