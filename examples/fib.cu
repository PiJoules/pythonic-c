def fib(n: int) -> int:
    if n < 2:
        return n 
    return fib(n-1) + fib(n-2)

def main():
    x = 30
    printf("fib #%d: %d\n", x, fib(x))
    return 0
