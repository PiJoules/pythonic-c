import ply.yacc as yacc

from clex import LEXER, tokens


class Node:
    __slots__ = tuple()

    def __init__(self, *args, **kwargs):
        for i, val in enumerate(args):
            setattr(self, self.__slots__[i], val)

        for attr in self.__slots__[len(args):]:
            setattr(self, attr, kwargs[attr])

    def lines(self):
        """
        Yields strings representing each line in the textual representation
        of this node. The tailing newline is excluded.
        """
        raise NotImplementedError

    def __str__(self):
        return "\n".join(self.lines())


class Module(Node):
    __slots__ = ("body", )

    def lines(self):
        for node in self.body:
            yield from node.lines()
            yield ""  # Extra newline


def p_module(p):
    "module : definition_list"
    p[0] = Module(p[1])


def p_definition_list_1(p):
    "definition_list : definition"
    p[0] = [p[1]]


def p_definition_list_2(p):
    "definition_list : definition_list definition"
    p[0] = p[1] + [p[2]]


class FuncDeclaration(Node):
    __slots__ = ("name", "args")

    def lines(self):
        yield "def {}({})".format(
            self.name,
            ", ".join(map(str, self.args))
        )


def p_definition_1(p):
    "definition : DEF ID LPAREN RPAREN"
    # Function declaration
    p[0] = FuncDeclaration(p[2], [])


def p_error(p):
    raise RuntimeError("No parser rule for {}".format(p))


PARSER = yacc.yacc()
LEXER_COPY = LEXER.clone()


def print_tokens():
    while True:
        tok = LEXER_COPY.token()
        if tok:
            print(tok)
        else:
            break


code = """
def main()
"""


def main():
    ast = PARSER.parse(code)
    return 0


if __name__ == "__main__":
    main()
