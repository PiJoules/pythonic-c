includel "ll.hpy"


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


#def list_prepend(l, i):
#    node = (Node[])malloc(sizeof(Node))
#    node->value = i 
#    node->next = l->head 
#    l->head = node
#    l->length = l->length + 1
