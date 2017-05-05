from cparse import Parser
from lang_ast import *


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
