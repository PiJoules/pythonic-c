#ifndef _OBJECT_H
#define _OBJECT_H

typedef struct Object Object;
struct Object {
    int x;
    int (*func)();
};

int Object_func(Object* self);

Object* new_Object();
void del_Object(Object* self);


typedef struct Person Person;
struct Person {
    Object* parent;

    int (*func)();
};

#endif
