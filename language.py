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
        dump_c_code_from_files(args.files)
    else:
        compile_lang_sources(args.files, output=args.output)


if __name__ == "__main__":
    main()
