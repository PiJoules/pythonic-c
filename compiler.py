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


def compile_c_sources(sources, asts, *, compiler="gcc", std="c11", output=None):
    # Keep only lang files
    c_sources = (s for s in sources if is_c_source(s))
    c_source_str = " ".join(c_sources)

    if not c_source_str:
        raise RuntimeError("No source files provided")

    if not output:
        output = "a.out"

    subprocess.run(
        "{compiler} -std={std} -o {output} {c_source_str}".format(**locals()).split(),
        check=True,
    )

    return output


def compile_asts(sources, asts, **kwargs):
    c_sources = []
    for i, source in enumerate(sources):
        c_sources.append(create_c_file(source, asts[i]))
    return compile_c_sources(c_sources, asts, **kwargs)


def compile_lang_sources(sources, **kwargs):
    """
    Takes a list of filenames, compiles them, and returns the executable.

    Args:
        source (list[str]): Source strings

    Returns:
        str: The final executable
    """
    asts = [file_to_ast(f) for f in sources]

    new_asts = []
    src_names = []
    for i, ast in enumerate(asts):
        source = sources[i]
        file_dir = os.path.dirname(source)

        # Find includes
        finder = IncludeFinder(file_dir)
        finder.visit(ast)
        includes = finder.includes()

        # Perform inference
        inferer = Inferer(source_file=source)
        src_names.append(source)
        new_asts.append(inferer.check(ast))

        # Do same dor includes
        for include in includes:
            inferer = Inferer(source_file=include)
            src_names.append(include)
            new_asts.append(inferer.check(file_to_ast(include)))

    return compile_asts(src_names, new_asts, **kwargs)


def file_to_ast(source):
    parser = Parser(source_file=source)
    with open(source, "r") as f:
        return parser.parse(f.read())


def dump_c_code_from_ast(ast):
    inferer = Inferer(source_file=ast.filename)
    new_ast = inferer.check(ast)
    print(new_ast.c_code())


def dump_c_code_from_file(source, *, dump_headers=True):
    print("------- {} --------".format(source))
    dump_c_code_from_ast(file_to_ast(source))


def run_files(sources, *, exe_args=None, **kwargs):
    """
    Compile and execute the files.

    Args:
        exe_args (optional[list[str]]): Extra arguments passed to the executable.
    """
    assert all(is_lang_file(s) for s in sources)

    # Compile
    out = compile_lang_sources(sources, **kwargs)

    cmd = [out] + (exe_args or [])

    # Execute
    return subprocess.run(
        cmd,
        check=True
    )
