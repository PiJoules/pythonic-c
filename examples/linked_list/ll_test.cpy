includel "ll.hpy" 
include "assert.hpy"


def main():
    lst = new_list()
    assert(not lst->length)
    free(lst)

    return 0
