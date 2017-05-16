#ifndef _LINKED_LIST_H
#define _LINKED_LIST_H
#include <stdlib.h>
typedef struct Node Node;
struct Node {int value; Node *next;};
typedef struct List List;
struct List {Node *head; size_t length;};
List* new_list();
void print_list(List *l);
void list_append(List *l, int i);
int list_pop(List *l);
#endif