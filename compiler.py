from cparse import Parser
from lang_ast import *
from inference import Inferer
from file_conversion import is_c_source, to_c_source

import subprocess
import os.path


def create_c_file(source, ast):
    c_fname = to_c_source(source)
    with open(c_fname, "w") as f:
        f.write(ast.c_code())

    return c_fname


def compile_sources(sources, asts, compiler="gcc", std="c11", output=None):
    c_sources = []
    for i, source in enumerate(sources):
        c_sources.append(create_c_file(source, asts[i]))

    # Keep only lang files
    c_sources = (s for s in c_sources if is_c_source(s))
    c_source_str = " ".join(c_sources)
    assert c_source_str

    if not output:
        output = "a.out"

    subprocess.run(
        "{compiler} -std={std} -o {output} {c_source_str}".format(**locals()).split(),
        check=True,
    )

    return output


def ast_for_file(source, parser=None):
    if parser is None:
        parser = Parser()
    with open(source, "r") as f:
        return parser.parse(f.read())


def dump_ast(source_dir, ast):
    inferer = Inferer(source_dir=source_dir)
    new_ast = inferer.check(ast)
    print(new_ast.c_code())

def dump_source(source):
    print("------- {} --------".format(source))
    dump_ast(source, ast_for_file(source))


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

    asts = [ast_for_file(f) for f in args.files]

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
            source = args.files[i]
            file_dir = os.path.dirname(source)

            # Find includes
            finder = IncludeFinder(file_dir)
            finder.visit(ast)

            for include in finder.includes():
                dump_source(include)
            print("------- {} --------".format(source))
            dump_ast(file_dir, ast)
    else:
        new_asts = []
        sources = []
        for i, ast in enumerate(asts):
            source = args.files[i]
            file_dir = os.path.dirname(source)

            # Find includes
            finder = IncludeFinder(file_dir)
            finder.visit(ast)
            includes = finder.includes()

            # Perform inference
            inferer = Inferer(source_dir=file_dir)
            sources.append(source)
            new_asts.append(inferer.check(ast))

            # Do same dor includes
            for include in includes:
                inferer = Inferer(source_dir=os.path.dirname(include))
                sources.append(include)
                new_asts.append(inferer.check(ast_for_file(include)))

        compile_sources(sources, new_asts, output=args.output)


if __name__ == "__main__":
    main()
