#ifndef _LINKED_LIST_H
#define _LINKED_LIST_H
typedef struct Node Node;
struct Node {int value; Node *next;};
typedef struct List List;
struct List {Node *head; int length;};
List* new_list();
void print_list(List *l);
void list_append(List *l, int i);
int list_pop(List *l);
#endif