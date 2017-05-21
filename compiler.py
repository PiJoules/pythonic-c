from cparse import Parser
from lang_ast import *
from inference import Inferer
from file_conversion import *

import subprocess
import os.path


def create_c_file(source, ast):
    assert is_lang_file(source)

    c_fname = to_c_file(source)
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


def file_to_ast(source):
    parser = Parser(source_file=source)
    with open(source, "r") as f:
        return parser.parse(f.read())


def dump_c_code_from_ast(ast):
    inferer = Inferer(source_file=ast.filename)
    new_ast = inferer.check(ast)
    print(new_ast.c_code())


def dump_c_code_from_source(source):
    print("------- {} --------".format(source))
    dump_c_code_from_ast(file_to_ast(source))
