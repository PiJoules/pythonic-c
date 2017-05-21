#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This is the program to be run on the command line when compiling sources

from compiler import *


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

    asts = [file_to_ast(f) for f in args.files]

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
                dump_c_code_from_file(include)
            print("------- {} --------".format(source))
            dump_c_code_from_ast(ast)
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
            inferer = Inferer(source_file=source)
            sources.append(source)
            new_asts.append(inferer.check(ast))

            # Do same dor includes
            for include in includes:
                inferer = Inferer(source_file=include)
                sources.append(include)
                new_asts.append(inferer.check(file_to_ast(include)))

        compile_sources(sources, new_asts, output=args.output)


if __name__ == "__main__":
    main()
