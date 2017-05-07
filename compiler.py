from cparse import Parser
from lang_ast import *


def create_c_file(source, ast):
    import os.path
    base, ext = os.path.splitext(source)
    c_fname = base + ".c"

    with open(c_fname, "w") as f:
        f.write(ast.c_code())

    return c_fname


def compile_sources(sources, asts, compiler="gcc", std="c11", output=None):
    import subprocess, os.path
    c_sources = []
    for i, source in enumerate(sources):
        c_sources.append(create_c_file(source, asts[i]))
    c_source_str = " ".join(c_sources)

    if not output:
        output = "a.out"

    subprocess.run(
        "{compiler} -std={std} -o {output} {c_source_str}".format(**locals()).split(),
        check=True,
    )

    return output


def get_args():
    from argparse import ArgumentParser
    parser = ArgumentParser()

    parser.add_argument("files", nargs="+")
    parser.add_argument("-t", "--tree", default=False, action="store_true",
                        help="Dump the ast tree")
    parser.add_argument("-d", "--dump", default=False, action="store_true",
                        help="Dump the original code with type inference added.")
    parser.add_argument("-p", "--print", default=False, action="store_true",
                        help="Dump the c representation of the code.")
    parser.add_argument("-o", "--output",
                        help="The name of the target executable.")
    parser.add_argument("-w", "--working-dir",
                        help="Working directory to store intermediate files.")

    return parser.parse_args()


def main():
    args = get_args()

    parser = Parser()

    asts = []
    for filename in args.files:
        with open(filename, "r") as f:
            asts.append(parser.parse(f.read()))

    if args.tree:
        for i, ast in enumerate(asts):
            print("------- {} --------".format(args.files[i]))
            print(dump_tree(ast))
    elif args.dump:
        for i, ast in enumerate(asts):
            print("------- {} --------".format(args.files[i]))
            print(ast)
    elif args.print:
        for i, ast in enumerate(asts):
            print("------- {} --------".format(args.files[i]))
            print(ast.c_code())
    else:
        compile_sources(args.files, asts, output=args.output)


if __name__ == "__main__":
    main()
