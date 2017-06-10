#include <stdio.h>
#include "bound_object.h"

int main(){
    Object* obj = new_Object();
    obj->x = 100;
    printf("%d\n", obj->func(obj));
    del_Object(obj);
    return 0;
}
