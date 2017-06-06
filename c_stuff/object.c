#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Object type 
#define OBJECT_ATTRS 

typedef struct Object Object;
struct Object {
    OBJECT_ATTRS
};

void Object___init__(Object* self){}
void Object___del__(Object* self){}
void Object_print(Object* self){
    printf("<Object %p>\n", self);
}

Object* new_Object(){
    Object* obj = (Object*)malloc(sizeof(Object));

    Object___init__(obj);

    return obj;
}

void del_Object(Object* obj){
    Object___del__(obj);
    free(obj);
}


// Person class 
// Inherits from Object  
#define PERSON_ATTRS OBJECT_ATTRS \
    char* name;

typedef struct Person Person;
struct Person {
    PERSON_ATTRS
};

void Person___init__(Person* self, char* name){
    self->name = (char*)malloc(strlen(name) + 1);
    strncpy(self->name, name, strlen(name));
    self->name[strlen(name)] = '\0';
}

void Person___del__(Person* self){
    free(self->name);
}

void Person_print(Person* self){
    printf("%s is a Person.\n", self->name);
}

Person* new_Person(char* name){
    Person* obj = (Person*)malloc(sizeof(Person));

    Person___init__(obj, name);

    return obj;
}

void del_Person(Person* self){
    Person___del__(self);
    free(self);
}

// Worker class 
// Inherits from Person and overrides print 
#define WORKER_ATTRS PERSON_ATTRS \
    int age;

typedef struct Worker Worker;
struct Worker {
    WORKER_ATTRS
};

void Worker_print(Worker* self){
    printf("%s is a Worker at age %d\n", self->name, self->age);
}

Worker* new_Worker(char* name){
    Worker* obj = (Worker*)malloc(sizeof(Worker));
    Person___init__((Person*)obj, name); // CALL INHERITED INIT WITHOUT HAVING TO TYPE PERSON
    return obj;
}

void del_Worker(Worker* self){
    Person___del__((Person*)self);  // CALL PARENT DEL WITHOUT HAVING TO TYPE PERSON
    free(self);
}

// Worker with name defined 
// Inherits from Worker and overrides __init__
#define WORKINGJON_ATTRS WORKER_ATTRS

typedef struct WorkingJon WorkingJon;
struct WorkingJon {
    WORKINGJON_ATTRS
};

void WorkignJon___init__(WorkingJon* self, int age){
    Person___init__((Person*)self, "Jon");  // CALL PARENT INIT WITHOUT HAVING TO TYPE PERSON 
    self->age = age;
}

WorkingJon* new_WorkingJon(int age){
    WorkingJon* obj = (WorkingJon*)malloc(sizeof(WorkingJon));
    WorkignJon___init__(obj, age);
    return obj;
}

void del_WorkingJon(WorkingJon* self){
    Person___del__((Person*)self);  // CALL PARENT DEL WITHOUT HAVING TO TYPE PERSON
    free(self);
}


int main(){
    Object* obj = new_Object();
    Object_print(obj);
    del_Object(obj);

    Person* person = new_Person("Bob");
    Person_print(person);
    del_Person(person);

    Worker* worker = new_Worker("Bib");
    worker->age = 30;
    Worker_print(worker);
    del_Worker(worker);

    WorkingJon* jon = new_WorkingJon(20);
    Worker_print((Worker*)jon);  // CALL PARENT PRINT WITHOUT HAVING TO TYPE WORKER
    del_WorkingJon(jon);

    return 0;
}
