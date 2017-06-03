/**
 * Function pointers do not mean anything
 */ 
#include <stdio.h>

int func(int a, int b){
    return a+b;
}

int (*glob_var)(int, int) = func;


typedef int t1(int, int);
typedef int (*t2(int, int));
//typedef t3 (int (*)(int, int));

struct S {
    int (*a)(int, int);
};

typedef enum enum_t enum_t;
enum enum_t {A, B, C};


int main(){
    printf("%zu\n", sizeof(func));
    printf("%zu\n", sizeof(*func));
    printf("%zu\n", sizeof(t1));
    printf("%zu\n", sizeof(t2));
    printf("%zu\n", sizeof(int));
    printf("%zu\n", sizeof(int*));
    printf("%zu\n", sizeof(int (*)(int, int)));
    //printf("%zu\n", sizeof(t3));

    struct S s;
    s.a = func;

    printf("%zu\n", sizeof(struct S));
    printf("%zu\n", sizeof(s));
    printf("%zu\n", sizeof(s.a));

    struct S s2;
    s2.a = &func;

    printf("%zu\n", sizeof(s2));
    printf("%zu\n", sizeof(s2.a));

    printf("s result: %d\n", s.a(1, 2));
    printf("s2 result: %d\n", s2.a(1, 2));

    int (*a)(int, int) = func;
    int (*b)(int, int) = &func;
    int (*c)(int, int) = *func;
    int (*d)(int, int) = **func;

    printf("a result: %d\n", a(3, 4));
    printf("b result: %d\n", b(3, 4));
    printf("c result: %d\n", c(3, 4));
    printf("d result: %d\n", d(3, 4));
    printf("*a result: %d\n", (*a)(3, 4));
    printf("*b result: %d\n", (*b)(3, 4));
    printf("*c result: %d\n", (*c)(3, 4));
    printf("**a result: %d\n", (**a)(3, 4));
    printf("**b result: %d\n", (**b)(3, 4));
    printf("**c result: %d\n", (**c)(3, 4));

    printf("a == b: %d\n", a == b);
    printf("b == c: %d\n", c == b);
    printf("c == d: %d\n", c == d);
    printf("a == func: %d\n", a == func);
    printf("*a == func: %d\n", *a == func);
    printf("*a == &func: %d\n", *a == &func);
    printf("glob_var == func: %d\n", glob_var == func);

    enum_t z = A;
    printf("A: %d\n", z);
    printf("B: %d\n", B);

    int arr[10] = {1, 2, 3};
    int arrc[10][10] = {1,2,3};

    int* ptr;
    // Both sides of these expressions must be integrals and returns integrals
    //2.0 << 4;
    //2.0 >> 4;
    //2 ^ 4.0;
    //2 | 4.0;
    //2 & 4.0;
    
    // Takes any types and always returns ints
    //2 || 4.0;
    //2 && 4.0;
    //2 > 4.0;
    //2 < 4.0;
    //2 >= 4.0;
    //2 <= 4.0;
    //2 != 4.0;
    //2 == 4.0;
    //4.0 % 2;  // Not logical but only takes integrals
    
    // Returns dominant types
    //2 / 4.0; 
    //2 * 4.0; 
    //2 - 4.0; 
    //2 + 4.0;  
    
    // Not entirely sure if you can cast to a function pointer still
    //t2* f = (t2*)func;
    //int res = (*f)(1, 2);
    //int res = ((t2*)func)(1, 2);

    t1* f = func;
    t2* f2 = (t2*)func;
    printf("%d\n", (f+2-2)(1, 2));  // Can call a binary expression 
    printf("%d\n", (&(*f))(1, 2));  // Can call an address-of
    printf("%d\n", (*f2)(1, 2));  // Can call a dereference
}
