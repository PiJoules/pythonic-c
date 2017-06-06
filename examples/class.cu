class A:
    def print(self: A*) -> void:
        printf("A\n")

def main():
    a = new_A()
    A_print(a)
    del_A(a)
    return 0
