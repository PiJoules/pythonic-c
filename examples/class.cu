class A:
    def print(self: A) -> void:
        printf("A\n")

def main():
    a = A()
    free(a)
    return 0
