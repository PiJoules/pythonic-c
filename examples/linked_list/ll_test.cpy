includel "ll.hpy" 
include "assert.hpy"


def main():
    lst = new_list()
    assert(not lst->length)
    del_list(lst)

    return 0
