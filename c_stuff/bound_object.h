#ifndef _OBJECT_H
#define _OBJECT_H

#define CALL(f, x) f->fn(f, x)

typedef struct Object Object;
struct Object {
    int x;
    int (*func)();
};

int Object_func(Object* self);

Object* new_Object();
void del_Object(Object* self);

#endif
