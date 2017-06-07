#include "bound_object.h"
#include <stdlib.h>

int Object_func(Object* self){
    return self->x;
}

// Want a data structure that remembers the instance and method 
typedef struct Functor Functor;
struct Functor {
    Object* self;
    int (*func)(Object* self);
};
int bound_func(Functor* functor){
    return functor->func(functor->self);
}

typedef int (*prep_func)(Object*);  // The prepared function that accepts the instance as the first arg 
typedef int (*called_func)();  // The called function that is bound to the func member in the struct 

called_func compose(prep_func func, Object* self){
}

void bind_func(Object* obj, int (*func)(Object* self)){
    obj->func = func;
}

Object* new_Object(){
    Object* obj = (Object*)malloc(sizeof(Object));

    //int Bound_Object_func(){
    //    return Object_func(obj);
    //}
    //obj->func = Bound_Object_func;
    bind_func(obj, Object_func);
    //obj->func = Object_func;

    return obj;
}

void del_Object(Object* self){
    free(self);
}
