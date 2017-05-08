ifndef _LINKED_LIST_H
define _LINKED_LIST_H

struct Node {
    value: int, 
    next: Node[],
}

struct List {
    head: Node[],
    length: int,
}

# Create a list
def new_list() -> List[]

# Print a list 
def print_list(l: List[]) -> void

# Append to a list 
def list_append(l: List[], i: int) -> void

# Pop from the list head
def list_pop(l: List[]) -> int

endif
