includel "ll.hpy" 
include "assert.h"


def main():
    lst = new_list()
    assert(not lst->length)
    free(lst)

    return 0
