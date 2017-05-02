from cparse import Parser
from lang_ast import *


class TypeInferer:
    @staticmethod
    def path_is_stdlib(path):
        return path in {
            "stdio.h",
        }

    def parse_include(self, node):
        path = node.s

        if self.path_is_stdlib(path):
            pass
        else:
            pass

    def parse(self, node):
        if isinstance(node, Module):
            self.parse(node)
        elif isinstance(node, list):
            self.parse_sequence(node)
        elif isinstance(node, Include):
            self.parse_include(node)
        else:
            raise RuntimeError("Unknown node {}".format(type(node)))

    def parse_sequence(self, seq):
        for node in seq:
            self.parse(node)

    def parse_module(self, node):
        self.parse_sequence(node.body)


def get_args():
    from argparse import ArgumentParser
    parser = ArgumentParser()

    parser.add_argument("filename")
    parser.add_argument("-t", "--tree", default=False, action="store_true")
    parser.add_argument("-d", "--dump", default=False, action="store_true")

    return parser.parse_args()


def main():
    args = get_args()

    parser = Parser()

    with open(args.filename, "r") as f:
        ast = parser.parse(f.read())

    if args.tree:
        print(dump_tree(ast))
    elif args.dump:
        print(ast)
    else:
        print(ast.c_code())


if __name__ == "__main__":
    main()
