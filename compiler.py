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


def compile_c_sources(sources, asts, *, compiler="gcc", std="c11", output=None,
                      optomize=2):
    # Keep only lang files
    c_sources = (s for s in sources if is_c_source(s))
    c_source_str = " ".join(c_sources)

    if not c_source_str:
        raise RuntimeError("No source files provided")

    if not output:
        output = "a.out"

    if optomize:
        optomize = "-O2"
    else:
        optomize = ""

    subprocess.run(
        "{compiler} -std={std} -o {output} {c_source_str} {optomize}"
        .format(**locals()).split(),
        check=True,
    )

    return output


def compile_asts(sources, asts, **kwargs):
    c_sources = []
    for i, source in enumerate(sources):
        c_sources.append(create_c_file(source, asts[i]))
    return compile_c_sources(c_sources, asts, **kwargs)


def compile_lang_sources_to_asts(sources, **kwargs):
    """
    Args:
        source (list[str]): Source strings

    Returns:
        dict[str, Node]: Mapping between the lang file and its type inferred ast
    """
    asts = [file_to_ast(f) for f in sources]

    src_map = {}
    for i, ast in enumerate(asts):
        source = sources[i]

        inferer = Inferer(source_file=source)
        src_map[source] = inferer.check(ast)

        # Add the includes found
        for include, include_ast in inferer.includes().items():
            if include not in src_map:
                src_map[include] = include_ast

    return src_map


def compile_lang_sources(sources, **kwargs):
    """
    Takes a list of filenames, compiles them, and returns the executable.

    Args:
        source (list[str]): Source strings

    Returns:
        str: The final executable
    """
    src_map = compile_lang_sources_to_asts(sources, **kwargs)
    src_names, inferred_asts = zip(*src_map.items())
    return compile_asts(src_names, inferred_asts, **kwargs)


def file_to_ast(source, **kwargs):
    assert is_lang_file(source)
    with open(source, "r") as f:
        return code_to_ast(f.read(), **kwargs)


def code_to_ast(code, *, infer=False, source_file=None):
    parser = Parser(source_file=source_file)
    ast = parser.parse(code)
    if infer:
        inferer = Inferer(source_file=source_file)
        ast = inferer.check(ast)
    return ast


def dump_c_code_from_ast(ast):
    inferer = Inferer(source_file=ast.filename)
    new_ast = inferer.check(ast)
    print(new_ast.c_code())


def dump_c_code_from_file(source, *, dump_headers=True):
    print("------- {} --------".format(source))
    dump_c_code_from_ast(file_to_ast(source))


def dump_c_code_from_files(sources, dump_headers=True, **kwargs):
    """Dump the C representation of the source files."""
    src_map = compile_lang_sources_to_asts(sources, **kwargs)
    for src, ast in src_map.items():
        print("------- {} --------".format(src))
        print(ast.c_code())


def dump_ast_trees(asts):
    for ast in asts:
        print("------- {} --------".format(ast.filename))
        print(dump_tree(ast))


def dump_ast_trees_from_files(sources):
    return dump_ast_trees(file_to_ast(s) for s in sources)


def run_files(sources, *, exe_args=None, stdout=None, input=None, **kwargs):
    """
    Compile and execute the files.

    Args:
        exe_args (optional[list[str]]): Extra arguments passed to the executable.
    """
    assert all(is_lang_file(s) for s in sources)

    # Compile
    out = compile_lang_sources(sources, **kwargs)
    cmd = ["./" + out] + (exe_args or [])

    # Execute
    return subprocess.run(
        cmd,
        check=True,
        stdout=stdout,
        input=input,
    )
