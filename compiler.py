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


def create_c_file(source, code):
    import os.path
    base, ext = os.path.splitext(source)
    c_fname = base + ".c"

    with open(c_fname, "w") as f:
        f.write(code)

    return c_fname


def compile_source(source, code, compiler="gcc", std="c11", output=None):
    import subprocess, os.path
    source = create_c_file(source, code)

    if not output:
        output = "a.out"

    subprocess.run(
        "{compiler} -std={std} -o {output} {source}".format(**locals()).split(),
        check=True,
    )

    return output


def get_args():
    from argparse import ArgumentParser
    parser = ArgumentParser()

    parser.add_argument("filename")
    parser.add_argument("-t", "--tree", default=False, action="store_true")
    parser.add_argument("-d", "--dump", default=False, action="store_true")
    parser.add_argument("-p", "--print", default=False, action="store_true")
    parser.add_argument("-o", "--output")

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
    elif args.print:
        print(ast.c_code())
    else:
        compile_source(args.filename, ast.c_code(), output=args.output)


if __name__ == "__main__":
    main()
