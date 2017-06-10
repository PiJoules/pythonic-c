#include "bound_object.h"
#include <stdlib.h>


// Object
int Object_func(Object* self){
    return self->x;
}

Object* new_Object(){
    Object* obj = (Object*)malloc(sizeof(Object));

    obj->func = Object_func;

    return obj;
}

void del_Object(Object* self){
    free(self);
}


// Person
int Person_func(Person* self){
    int parent_x = self->parent->x;
    return -10;
}

Person* new_Person(){
    Person* obj = (Person*)malloc(sizeof(Person));

    obj->func = Person_func;

    return obj;
}
