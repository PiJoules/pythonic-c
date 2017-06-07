class A:
    x = 0

    def print(self: A*) -> void:
        printf("A: %d\n", self->x)

    def __init__(self: A*, x: int) -> void:
        self->x = x

def main():
    a = new_A(10)
    A_print(a)
    del_A(a)

    return 0
